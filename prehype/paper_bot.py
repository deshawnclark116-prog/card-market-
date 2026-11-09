"""Thirty-day $100 reference-card PAPER experiment.

No real orders, no eBay purchases, no fabricated listing prices.
Simulated entries use recent SOLD-comparable medians (a broad card-type
reference, NOT an exact verified purchasable listing). Slippage, shipping,
and selling fees make the accounting deliberately conservative.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import date, timedelta
from pathlib import Path
from statistics import median
from typing import Callable

START_CENTS = 10_000
TRIAL_DAYS = 30
MAX_ENTRY_CENTS = 2_500
MAX_POSITIONS = 5
MAX_BUYS_PER_DAY = 1
MIN_COMPS = 5
RECENT_DAYS = 45
FRESH_SALE_DAYS = 14
MIN_DEAL_SCORE = 50.0
MIN_BREAKOUT_SCORE = 45.0
BUY_SLIPPAGE_RATE = 0.05
BUY_SHIPPING_CENTS = 350
SELL_FEE_RATE = 0.15
SELL_SHIPPING_CENTS = 350
CARDS = ("Bowman 1st auto", "Rookie auto")
DEFAULT_LEDGER = "data/card_bot_100.json"
QuoteLookup = Callable[[str, str, date], dict | None]


def make_ledger(today: date) -> dict:
    return {
        "schema": 1,
        "mode": "PAPER_REFERENCE_CARD_PROXY_NO_REAL_TRADES",
        "started_on": today.isoformat(),
        "ends_on": (today + timedelta(days=TRIAL_DAYS)).isoformat(),
        "starting_cash_cents": START_CENTS,
        "cash_cents": START_CENTS,
        "positions": [],
        "events": [],
        "daily_runs": [],
    }


def load_ledger(path: str, today: date) -> dict:
    target = Path(path)
    if not target.exists():
        return make_ledger(today)
    with target.open(encoding="utf-8") as fh:
        state = json.load(fh)
    if state.get("schema") != 1 or state.get("mode") != "PAPER_REFERENCE_CARD_PROXY_NO_REAL_TRADES":
        raise ValueError("Unrecognized paper-bot ledger; refusing to alter it")
    if state.get("starting_cash_cents") != START_CENTS:
        raise ValueError("Unexpected bankroll; refusing to alter ledger")
    return state


def save_ledger(path: str, state: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=target.name + ".", dir=target.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def card_id(player: str, card: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (player + "-" + card).lower()).strip("-")


def _integer_cents(dollars: float) -> int:
    return int(round(float(dollars) * 100))


def _entry_cost(median_cents: int) -> int:
    return int(round(median_cents * (1.0 + BUY_SLIPPAGE_RATE))) + BUY_SHIPPING_CENTS


def _liquidation_value(median_cents: int) -> int:
    """Estimated net proceeds if a buyer can be found at the SOLD median."""
    return max(0, int(round(median_cents * (1.0 - SELL_FEE_RATE))) - SELL_SHIPPING_CENTS)


def make_live_quote_lookup() -> QuoteLookup:
    """Reuse the repository's existing eBay sold-comps source.

    Recency is checked here; its existing API board only exposes comp counts,
    not the individual sold dates. Do not use a demo price or a missing quote.
    """
    from prehype.breakouts import CARD_QUERY_BUILDERS, CARD_LABELS
    from prehype.sources.ebay import EbayCompsClient, trim_price_outliers

    client = EbayCompsClient()
    builders = {CARD_LABELS[key]: builder for key, builder in CARD_QUERY_BUILDERS.items()}
    memo: dict[tuple[str, str, str], dict | None] = {}

    def lookup(player: str, card: str, as_of: date) -> dict | None:
        key = (player, card, as_of.isoformat())
        if key in memo:
            return memo[key]
        builder = builders.get(card)
        if builder is None:
            memo[key] = None
            return None
        comps = trim_price_outliers(client.sold_comps(builder(player)))
        window = as_of - timedelta(days=RECENT_DAYS)
        recent = [c for c in comps if window <= c.sold_on <= as_of and c.price > 0]
        if not recent:
            memo[key] = None
            return None
        last_sale = max(c.sold_on for c in recent)
        quote = {
            "median_cents": _integer_cents(median(c.price for c in recent)),
            "comps": len(recent),
            "last_sale": last_sale.isoformat(),
            "source": "eBay sold comps; broad reference-card search",
        }
        memo[key] = quote
        return quote

    return lookup


def _quote_is_fresh(quote: dict | None, day: date, *, minimum: int = MIN_COMPS) -> bool:
    if not quote:
        return False
    try:
        n = int(quote["comps"])
        price = int(quote["median_cents"])
        last_sale = date.fromisoformat(quote["last_sale"])
    except (ValueError, TypeError, KeyError):
        return False
    return n >= minimum and price > 0 and 0 <= (day - last_sale).days <= FRESH_SALE_DAYS


def _ranked_options(candidates: list[dict]) -> list[tuple[float, str, dict]]:
    result = []
    for candidate in candidates:
        try:
            deal = float(candidate["dealScore"])
            breakout = float(candidate["breakoutScore"])
            trend = candidate["priceTrend"]
            hype = candidate["hypePct"]
            if (deal < MIN_DEAL_SCORE or breakout < MIN_BREAKOUT_SCORE
                    or trend is None or float(trend) > 0.15
                    or hype is None or float(hype) > 30.0):
                continue
            name = candidate["name"].strip()
            if not name:
                continue
            for card in CARDS:
                if card in candidate.get("cards", {}):
                    result.append((deal, card, candidate))
        except (TypeError, KeyError, ValueError, AttributeError):
            continue
    return sorted(result, key=lambda row: (-row[0], row[2]["name"], row[1]))


def simulate_day(state: dict, candidates: list[dict], quote_lookup: QuoteLookup, day: date) -> dict:
    """One idempotent daily decision, without real money or external writes."""
    today = day.isoformat()
    previous = next((r for r in state["daily_runs"] if r["date"] == today), None)
    if previous is not None:
        return previous

    # Mark ALL held references, even if their players fell off today's shortlist.
    marks_updated = 0
    for position in state["positions"]:
        quote = quote_lookup(position["player"], position["card"], day)
        if _quote_is_fresh(quote, day):
            position["last_mark_cents"] = int(quote["median_cents"])
            position["last_mark_date"] = today
            position["last_mark_comps"] = int(quote["comps"])
            marks_updated += 1

    run = {
        "date": today,
        "candidate_count": len(candidates),
        "marks_updated": marks_updated,
        "buys": [],
        "status": "NO_QUALIFYING_VERIFIED_COMPS",
    }
    if day < date.fromisoformat(state["started_on"]):
        raise ValueError("Run date predates ledger creation")
    if day >= date.fromisoformat(state["ends_on"]):
        run["status"] = "TRIAL_COMPLETE_NO_NEW_BUYS"
    elif len(state["positions"]) >= MAX_POSITIONS:
        run["status"] = "POSITION_LIMIT"
    else:
        already_held = {p["id"] for p in state["positions"]}
        already_players = {p["player"].casefold() for p in state["positions"]}
        for _, card, candidate in _ranked_options(candidates):
            if len(run["buys"]) >= MAX_BUYS_PER_DAY or len(state["positions"]) >= MAX_POSITIONS:
                break
            player = candidate["name"].strip()
            identity = card_id(player, card)
            if identity in already_held or player.casefold() in already_players:
                continue
            quote = quote_lookup(player, card, day)
            if not _quote_is_fresh(quote, day):
                continue
            median_cents = int(quote["median_cents"])
            entry_cents = _entry_cost(median_cents)
            if median_cents < 500 or entry_cents > MAX_ENTRY_CENTS:
                continue
            if entry_cents > state["cash_cents"]:
                continue
            position = {
                "id": identity,
                "player": player,
                "card": card,
                "entry_date": today,
                "entry_reference_median_cents": median_cents,
                "entry_total_cents": entry_cents,
                "entry_comps": int(quote["comps"]),
                "deal_score_not_probability": float(candidate["dealScore"]),
                "breakout_score_not_probability": float(candidate["breakoutScore"]),
                "last_mark_cents": median_cents,
                "last_mark_date": today,
                "last_mark_comps": int(quote["comps"]),
                "fill_type": "SIMULATED_SOLD_MEDIAN_PROXY_NOT_A_REAL_LISTING",
            }
            state["positions"].append(position)
            state["cash_cents"] -= entry_cents
            event = {
                "date": today,
                "type": "PAPER_BUY_REFERENCE_ONLY",
                "position_id": identity,
                "player": player,
                "card": card,
                "entry_total_cents": entry_cents,
                "reference_median_cents": median_cents,
                "comps": int(quote["comps"]),
            }
            state["events"].append(event)
            run["buys"].append(event)
            run["status"] = "PAPER_BUY_RECORDED"
            already_held.add(identity)
            already_players.add(player.casefold())
    state["daily_runs"].append(run)
    return run


def report(state: dict, today: date) -> dict:
    estimated_net = 0
    stale = 0
    positions = []
    for p in state["positions"]:
        mark = p.get("last_mark_cents")
        mark_day = p.get("last_mark_date")
        is_fresh = (mark is not None and mark_day == today.isoformat())
        if not is_fresh:
            stale += 1
        exit_value = _liquidation_value(int(mark)) if mark is not None else None
        if exit_value is not None:
            estimated_net += exit_value
        positions.append({
            "player": p["player"],
            "card": p["card"],
            "paper_entry_total_usd": round(p["entry_total_cents"] / 100, 2),
            "last_reference_median_usd": round(mark / 100, 2) if mark is not None else None,
            "estimated_net_exit_usd": round(exit_value / 100, 2) if exit_value is not None else None,
            "mark_date": mark_day,
            "mark_fresh_today": is_fresh,
            "note": "Card category proxy; not a specific verified listing",
        })
    gross_paper_value = state["cash_cents"] + estimated_net
    return {
        "mode": state["mode"],
        "started_on": state["started_on"],
        "ends_on": state["ends_on"],
        "status": "COMPLETE" if today >= date.fromisoformat(state["ends_on"]) else "IN_PROGRESS",
        "initial_cash_usd": state["starting_cash_cents"] / 100,
        "cash_remaining_usd": round(state["cash_cents"] / 100, 2),
        "number_of_paper_buys": len(state["events"]),
        "days_recorded": len(state["daily_runs"]),
        "positions": positions,
        "stale_or_unverified_marks": stale,
        "indicative_net_liquidation_usd": (round(gross_paper_value / 100, 2)
                                          if stale == 0 else None),
        "indicative_return_pct": (round((gross_paper_value / state["starting_cash_cents"] - 1) * 100, 2)
                                  if stale == 0 else None),
        "important": ("Estimated liquidation is NOT realized profit and assumes "
                      "a buyer exists at the recent sold median. All entries "
                      "are synthetic category-level fills, not matched live listings."),
    }


def market_data_ready(candidates: list[dict], quote_lookup: QuoteLookup, day: date) -> bool:
    """Only start the 30-day clock when fresh tradeable reference data exists."""
    for candidate in candidates:
        player = candidate.get("name")
        if not isinstance(player, str) or not player.strip():
            continue
        cards = candidate.get("cards") or {}
        for card in CARDS:
            if card in cards and _quote_is_fresh(quote_lookup(player, card, day), day):
                return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="$100 / 30-day sports-card PAPER bot")
    parser.add_argument("command", choices=("run", "report"))
    parser.add_argument("--ledger", default=DEFAULT_LEDGER)
    args = parser.parse_args()
    today = date.today()
    state = load_ledger(args.ledger, today)
    if args.command == "run":
        # LIVE only: canned api.DEMO_DATA must never enter the paper ledger.
        from prehype.api import run_scan
        from prehype.scouting_report import build_scouting_report, save_scouting_report
        candidates = run_scan(scan_type="both", top=15, prices=True, hype=True, use_cache=False)
        lookup = make_live_quote_lookup()
        if not Path(args.ledger).exists() and not market_data_ready(candidates, lookup, today):
            status = "WAITING_FOR_LIVE_MARKET_DATA"
            run = {"status": status, "candidate_count": len(candidates), "buys": []}
        else:
            run = simulate_day(state, candidates, lookup, today)
            status = run["status"]
            save_ledger(args.ledger, state)
        scouting = build_scouting_report(candidates, lookup, today, state, status, run["buys"])
        save_scouting_report(scouting)
        print(json.dumps(run, indent=2))
        print(f"Daily scouting board: CARD_BOT_DASHBOARD.md ({scouting['players_screened']} players)")
    print(json.dumps(report(state, today), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
