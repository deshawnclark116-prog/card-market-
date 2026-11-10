"""Read-only visibility into every player and reference card the paper bot screens."""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from prehype.paper_bot import (
    CARDS, MAX_ENTRY_CENTS, MAX_POSITIONS, MIN_BREAKOUT_SCORE, MIN_COMPS,
    MIN_DEAL_SCORE, FRESH_SALE_DAYS, _entry_cost, _quote_is_fresh,
    card_id, report,
)

DEFAULT_SCOUTING_JSON = "data/card_bot_scouting_latest.json"
DEFAULT_DASHBOARD = "CARD_BOT_DASHBOARD.md"

def _number(x):
    try:
        v = float(x)
        return v if v == v and abs(v) != float("inf") else None
    except (TypeError, ValueError):
        return None

def _score_reasons(candidate):
    reasons = []
    deal = _number(candidate.get("dealScore"))
    breakout = _number(candidate.get("breakoutScore"))
    hype = _number(candidate.get("hypePct"))
    trend = _number(candidate.get("priceTrend"))
    if deal is None or deal < MIN_DEAL_SCORE:
        reasons.append("missing or low deal score")
    if breakout is None or breakout < MIN_BREAKOUT_SCORE:
        reasons.append("missing or low breakout score")
    if hype is None:
        reasons.append("hype data missing")
    elif hype > 30:
        reasons.append("already too much hype")
    if trend is None:
        reasons.append("price trend missing")
    elif trend > .15:
        reasons.append("price rising too quickly")
    return reasons

def build_scouting_report(candidates, lookup, day: date, state, run_status, buys=()):
    """Display actual score gates, SOLD-median quotes and daily paper decisions.

    Never modifies positions or cash. The quote source is not a live listing.
    """
    bought_ids = {b["position_id"] for b in buys}
    held_ids = {p["id"] for p in state["positions"]}
    held_players = {p["player"].casefold() for p in state["positions"]}
    sorted_candidates = sorted(
        candidates, key=lambda c: (-(_number(c.get("dealScore")) or -1),
                                   str(c.get("name", "")).casefold()))
    players = []
    for index, candidate in enumerate(sorted_candidates, 1):
        name = str(candidate.get("name") or "").strip()
        score_reasons = _score_reasons(candidate)
        checks = []
        for card in (candidate.get("cards") or {}):
            quote = (lookup.peek(name, card, day) if hasattr(lookup, "peek") else lookup(name, card, day)) if name else None
            fresh = _quote_is_fresh(quote, day)
            median_cents = int(quote["median_cents"]) if fresh else None
            entry_cents = ((int(round(median_cents * 1.10)) + 350)
                           if fresh and quote.get("source") == "cardpricer_public_exact_sold_proxy"
                           else (_entry_cost(median_cents) if fresh else None))
            reasons = list(score_reasons)
            if not fresh:
                reasons.append("no 5 independently title-matched recent sales of this EXACT card/grade")
            elif median_cents < 500:
                reasons.append("reference price under 5 dollars")
            elif entry_cents > MAX_ENTRY_CENTS:
                reasons.append("over 25 dollar all-in purchase cap")
            elif entry_cents > state["cash_cents"] and card_id(name, card) not in held_ids:
                reasons.append("insufficient unspent cash")
            identity = card_id(name, card)
            was_checked = (getattr(lookup, "checked_card", None) == {"player": name, "card": card})
            if identity in bought_ids:
                decision = "PAPER BOUGHT TODAY"
            elif identity in held_ids or name.casefold() in held_players:
                decision = "ALREADY HELD"
            elif not fresh and hasattr(lookup, "cards_found"):
                decision = "PRICE GUIDE ONLY (NOT VERIFIED BUY)"
            elif not fresh and not was_checked and hasattr(lookup, "peek"):
                decision = "NOT CHECKED (API QUOTA)"
                reasons = ["Daily request budget: checking one reference card per day"]
            elif reasons:
                decision = "PASS"
            elif len(state["positions"]) >= MAX_POSITIONS:
                decision = "WAITLIST (position cap)"
            else:
                decision = "QUALIFIED (not selected today)"
            checks.append({
                "card": card, "decision": decision, "reasons": reasons,
                "sold_median_usd": round(median_cents/100,2) if fresh else None,
                "catalog_guide_price_usd": (candidate.get("cards") or {}).get(card,{}).get("price"),
                "card_id": (candidate.get("cards") or {}).get(card,{}).get("card_id"),
                "all_in_paper_usd": round(entry_cents/100,2) if fresh else None,
                "sold_comps": int(quote["comps"]) if quote else None,
                "last_sale": quote.get("last_sale") if quote else None,
                "quote_fresh": fresh,
                "listing_url": quote.get("listing_url") if quote else None,
                "listing_title": quote.get("listing_title") if quote else None,
                "variant_key": quote.get("variant_key") if quote else None,
                "active_offer_all_in_usd": round(int(quote["all_in_ask_cents"])/100,2) if quote and quote.get("all_in_ask_cents") else None,
                "provenance_url": quote.get("provenance_url") if quote else None,
                "note": ("Exact card-grade verified sold-price PAPER proxy; no live listing"
                         if quote and quote.get("source") == "cardpricer_public_exact_sold_proxy"
                         else "Unverified price guide unless exact sold comps exist"),
            })
        players.append({
            "rank": index, "name": name,
            "position": candidate.get("position"),
            "deal_score_not_probability": candidate.get("dealScore"),
            "breakout_score_not_probability": candidate.get("breakoutScore"),
            "hype_pct": candidate.get("hypePct"),
            "price_trend": candidate.get("priceTrend"),
            "reason": candidate.get("reason"),
            "checks": checks,
        })
    return {
        "as_of": day.isoformat(), "status": run_status,
        "source": "LIVE MLB scanner plus public anonymous card sales; never demo",
        "players_screened": len(players),
        "players": players, "paper_buys_today": list(buys),
        "portfolio": report(state, day),
        "note": "Paper fills use historical sold-price category medians, NOT live listings.",
    }

def _clean(value):
    if value is None:
        return "—"
    return str(value).replace("|", "/").replace("\n"," ").replace("\r"," ")

def _money(value):
    return ("USD " + f"{value:.2f}") if value is not None else "unknown"

def to_markdown(data):
    port = data["portfolio"]
    lines = [
        "# Card Bot — Daily Scouting Board", "",
        f"**Last scan:** {data['as_of']} | **Status:** {_clean(data['status'])}", "",
        "**Paper-only experiment:** verified reference-card sold-price proxies, not active offers. "
        "Catalog price estimates are NEVER used as paper purchase prices.",
        "", "## Current paper bankroll", "",
        f"- Cash remaining: **{_money(port['cash_remaining_usd'])}**",
        f"- Paper purchases recorded: **{port['number_of_paper_buys']}**",
        f"- Players considered today: **{data['players_screened']}**",
        f"- Estimated net liquidation, not realized: **{_money(port['indicative_net_liquidation_usd']) if port['indicative_net_liquidation_usd'] is not None else 'unavailable due to stale marks'}**",
        "", "## Paper holdings", "",
    ]
    market = data.get("market_data") or {}
    if market:
        lines += ["", "## Live pricing diagnostics", "",
                  "- Provider: **CardPricer public anonymous API** (no key/account)",
                  "- HTTP requests this scan: **" + str(market.get("requests_used", 0)) + "**",
                  "- MLB players checked for public cards: **" + str(market.get("players_checked", 0)) + "**",
                  "- Catalog cards discovered: **" + str(market.get("catalog_card_rows", 0)) + "**",
                  "- Exact variant prices with >=5 independently title-matched sales: **" + str(market.get("card_variants_with_independent_five_sale_match", 0)) + "**",
                  "- Feed status: **" + _clean(market.get("last_error") or "No API error reported") + "**",
                  "- These catalog prices are INDICATIVE and NOT proof of available inventory.", ""]
    if not port["positions"]:
        lines.append("No paper holdings yet.")
    else:
        lines += ["| Player | Card reference | All-in entry | Estimated net exit |", "|---|---|---:|---:|"]
        for p in port["positions"]:
            lines.append(f"| {_clean(p['player'])} | {_clean(p['card'])} | {_money(p['paper_entry_total_usd'])} | {_money(p['estimated_net_exit_usd'])} |")
    lines += ["", "## Players considered", ""]
    if not data["players"]:
        lines.append("**No candidates returned.** This may mean source coverage was empty or unavailable; it does not imply no good cards exist.")
    else:
        lines += ["| Rank | Player | Deal score | Breakout | Hype | Price trend |",
                  "|---:|---|---:|---:|---:|---:|"]
        for p in data["players"]:
            trend = f"{float(p['price_trend'])*100:+.1f}%" if p["price_trend"] is not None else "unknown"
            lines.append(f"| {p['rank']} | {_clean(p['name'])} | {_clean(p['deal_score_not_probability'])} | {_clean(p['breakout_score_not_probability'])} | {_clean(p['hype_pct'])}% | {trend} |")
        lines += ["", "## Each card checked and why", "",
                  "| Player | Exact card and grade | Guide only | Verified sold median | Verified sales | Decision | Reasons |",
                  "|---|---|---:|---:|---:|---|---|"]
        for p in data["players"]:
            for c in p["checks"]:
                reasons = "; ".join(c["reasons"]) or "Meets filters; daily limit/ranking may apply"
                lines.append(f"| {_clean(p['name'])} | {_clean(c['card'])} | {_money(c['catalog_guide_price_usd'])} | {_money(c['sold_median_usd'])} | {_clean(c['sold_comps'])} | {_clean(c['decision'])} | {_clean(reasons)} |")
        lines += ["", "## Player skill-change explanations", ""]
        for p in data["players"]:
            if p["reason"]:
                lines.append(f"- **{_clean(p['name'])}:** {_clean(p['reason'])}")
    lines += ["", "---", "Not a guarantee of profits. Scores are NOT win probabilities. No NBA/NFL analysis is performed by this version.", ""]
    return "\n".join(lines)

def save_scouting_report(data, json_path=DEFAULT_SCOUTING_JSON, md_path=DEFAULT_DASHBOARD):
    for target in (Path(json_path), Path(md_path)):
        target.parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path(md_path).write_text(to_markdown(data), encoding="utf-8")
