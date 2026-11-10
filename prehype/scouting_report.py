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
    if candidate.get("cardHypeVerified") is False:
        reasons.append("card-collector hype NOT measured; search ratio is not proof of quiet demand")
    elif hype is None:
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
    # Never sort alphabetically just because every deal score is unavailable.
    # Distinguish a skill-change watchlist from an investable deal ranking.
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (
            0 if _number(c.get("dealScore")) is not None else 1,
            -(_number(c.get("dealScore")) or 0),
            -((c.get("earlySignal") or {}).get("evidence_tier_order") or 0),
            -(_number(c.get("breakoutScore")) or 0),
            str(c.get("name", "")).casefold(),
        ),
    )
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
                # Keep vendor values in JSON for audit but do not print
                # unvalidated source estimates as market prices.
                "catalog_raw_untrusted_usd": (candidate.get("cards") or {}).get(card,{}).get("price"),
                "catalog_guide_price_usd": None,
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
            "level": candidate.get("level"),
            "age": candidate.get("age"),
            "player_id": candidate.get("playerId"),
            "time_context": candidate.get("timeContext"),
            "market_exposure": candidate.get("marketExposure"),
            "early_signal": candidate.get("earlySignal"),
            "deal_score_not_probability": candidate.get("dealScore"),
            "breakout_score_not_probability": candidate.get("breakoutScore"),
            "hype_pct": candidate.get("hypePct") if candidate.get("cardHypeVerified") is not False else None,
            "search_interest_vs_aaron_judge_pct": candidate.get("searchInterestVsJudgePct"),
            "collector_hype_status": ("NOT MEASURED" if candidate.get("cardHypeVerified") is False
                                     else "LEGACY UNVERIFIED"),
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
        "**Paper-only experiment:** unverified catalog dollar values are HIDDEN. "
        "A verified same-card sale median is NOT an active offer. "
        "A player skill-change score is NOT an investment score.",
        "", "## Current paper bankroll", "",
        f"- Cash remaining: **{_money(port['cash_remaining_usd'])}**",
        f"- Paper purchases recorded: **{port['number_of_paper_buys']}**",
        f"- Players considered today: **{data['players_screened']}**",
        f"- Estimated net liquidation, not realized: **{_money(port['indicative_net_liquidation_usd']) if port['indicative_net_liquidation_usd'] is not None else 'unavailable due to stale marks'}**",
        "", "## Paper holdings", "",
    ]
    discovery = data.get("discovery") or {}
    if discovery:
        lines += ["",
                  "## What the bot is actually hunting", "",
                  "**GOAL:** Younger MiLB players whose strikeout discipline, walk discipline "
                  "and extra-base-hit production are improving *before* public recognition. "
                  "This is **NOT** a ranked list of hyped MLB breakout stars.", "",
                  "- Discovery source: **Official MLB StatsAPI minor-league season stats and player game logs**",
                  "- Season reviewed: **" + str(discovery.get("season","?")) + "**",
                  "- Context: **" + ("OFFSEASON / retrospectively reviewing last season (no new games today)"
                                    if discovery.get("offseason") else
                                    "IN-SEASON / recent games") + "**",
                  "- MiLB season rows read: **" + str(discovery.get("season_stat_rows",0)) + "**",
                  "- Player game-log feeds with data: **" + str(discovery.get("game_log_records_available_for_players",0)) + "**",
                  "- Skill-change candidates: **" + str(discovery.get("independent_skill_changes_found",0)) + "**",
                  "- Comparison periods: **14v14, 28v28, 42v42** (up to 84 games of history); longer periods are overlapping diagnostics, not independent trials",
                  "- Evidence tiers: **" + _clean(discovery.get("evidence_tier_counts") or {}) + "**",
                  "- Levels unavailable: **" + _clean(discovery.get("minor_league_levels_missing") or "none") + "**",
                  "- Major-league exposure filter: **" + ("available" if discovery.get("exposure_filter_source_available") else "UNAVAILABLE — exposure unconfirmed") + "**",
                  "- A skill-change signal is NOT proof of low card-market hype or a fair card price.",
                  ""]
        already = discovery.get("already_publicized_excluded") or []
        if already:
            lines += ["### Already-publicized names removed from early shortlist", "",
                      "These players passed some raw skill-change checks, but are "
                      "already publicly ranked prospects. **They are NOT pre-hype picks.**", "",
                      "| Player | Skill score (not probability) | Reason for exclusion |",
                      "|---|---:|---|"]
            for player in already:
                lines.append(f"| {_clean(player['name'])} | "
                             f"{_clean(player.get('skill_score'))} | "
                             f"[Already on a published Top-100 list]({discovery.get('public_top100_source')}) |")
            lines.append("")
        if not discovery.get("public_top100_source_available"):
            lines += ["**Public ranking check unavailable — nobody is labeled 'unhyped'.**", ""]
    market = data.get("market_data") or {}
    if market:
        lines += ["", "## Live pricing diagnostics", "",
                  "- Provider: **[CardPricer public anonymous API](https://cardpricer.co)** (no key/account)",
                  "- HTTP requests this scan: **" + str(market.get("requests_used", 0)) + "**",
                  "- MLB players checked for public cards: **" + str(market.get("players_checked", 0)) + "**",
                  "- Catalog cards discovered: **" + str(market.get("catalog_card_rows", 0)) + "**",
                  "- Exact variant prices with >=5 independently title-matched sales: **" + str(market.get("card_variants_with_independent_five_sale_match", 0)) + "**",
                  "- Feed status: **" + _clean(market.get("last_error") or "No API error reported") + "**",
                  "- Catalog price estimates: **QUARANTINED / NOT SHOWN** (independent values disagreed substantially).",
                  "- Card-collector hype: **NOT VERIFIED**. Google search interest relative to Aaron Judge is not card demand.",
                  "- Paper buying from unverified card-attention data: **BLOCKED**.", ""]
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
        if discovery:
            lines += [
                "**Early-signal strength is a heuristic, NOT a profit probability.** "
                "Longer-window evidence is ranked ahead of short-lived spikes. "
                "None are confirmed cheap or unnoticed cards.",
                "",
                "| Evidence rank | Player | Level | Age | Persistence tier | Heuristic score | Last game | Collector interest |",
                "|---:|---|---|---:|---|---:|---|---|",
            ]
            tier_names = {
                "SUSTAINED_ACROSS_14_28_42":"SUSTAINED — three horizons",
                "BUILDING_14_AND_28":"BUILDING — 14 + 28",
                "EARLY_14_ONLY":"EARLY — not confirmed",
                "SHORT_SPIKE_NOT_CONFIRMED":"SHORT SPIKE — not confirmed",
                "LONG_HORIZON_CONFLICT":"LONG WINDOW CONFLICT",
            }
            for p in data["players"]:
                signal=p.get("early_signal") or {}
                tier=signal.get("evidence_tier")
                lines.append(
                    f"| {p['rank']} | {_clean(p['name'])} | {_clean(p.get('level'))} | "
                    f"{_clean(p.get('age'))} | {_clean(tier_names.get(tier,tier or 'UNKNOWN'))} | "
                    f"{_clean(p.get('breakout_score_not_probability'))} | "
                    f"{_clean(signal.get('last_game'))} | **NOT VERIFIED** |"
                )
            lines += [
                "",
                "## Multi-window skill evidence — fluke or sustained?",
                "",
                "Each row compares the most recent N games against the **immediately preceding N games**. "
                "All data are as of the scan date and must remain on the same MiLB team. "
                "Horizons overlap; confidence-support figures are descriptive, **NOT** "
                "probabilities of future breakout.",
                "",
                "| Player | Window | Before → after K% | Before → after BB% | Before → after ISO | Supported metrics | Result |",
                "|---|---|---|---|---|---|---|",
            ]
            for p in data["players"]:
                comps=(p.get("early_signal") or {}).get("comparisons") or {}
                for n in ("14","28","42"):
                    c=comps.get(n) or {}
                    status=c.get("status","UNAVAILABLE")
                    if status!="AVAILABLE":
                        lines.append(f"| {_clean(p['name'])} | {n} vs {n} | — | — | — | — | {_clean(status.replace('_',' '))} |")
                        continue
                    old, new = c["old"], c["new"]
                    a_k=f"{old['k_pct']:.1%} → {new['k_pct']:.1%}"
                    a_bb=f"{old['bb_pct']:.1%} → {new['bb_pct']:.1%}"
                    a_iso=f"{old['iso']:.3f} → {new['iso']:.3f}"
                    supported=", ".join(c.get("supporting_metrics") or []) or "none"
                    verdict=("SUPPORTS CHANGE" if c.get("confirmed")
                             else "NOT CONFIRMED")
                    lines.append(
                        f"| {_clean(p['name'])} | {n} vs {n} "
                        f"({old['pa']}/{new['pa']} PA) | {a_k} | {a_bb} | "
                        f"{a_iso} | {_clean(supported)} | {verdict} |"
                    )
            lines += [
                "",
                "**Interpretation:** A big 14-game move with no 28-game support "
                "is a possible fluke. Agreement across longer windows strengthens "
                "the evidence but does not prove the player's true future talent, "
                "exclude different opponents/parks, or predict the card market.",
                "",
            ]
        else:
            lines += [
                "**Ranked by underlying skill change when verified deal scores are unavailable.**",
                "Search interest is NOT verified card-collector demand.", "",
                "| Skill rank | Player | Breakout score | Searches vs. Judge | Collector hype | Verified deal score |",
                "|---:|---|---:|---:|---|---:|",
            ]
            for p in data["players"]:
                ratio=p.get("search_interest_vs_aaron_judge_pct")
                shown=("not available" if ratio is None else f"{ratio}% of Judge")
                lines.append(f"| {p['rank']} | {_clean(p['name'])} | "
                             f"{_clean(p['breakout_score_not_probability'])} | {shown} | "
                             f"{_clean(p['collector_hype_status'])} | "
                             f"{_clean(p['deal_score_not_probability'])} |")
        lines += ["", "## Card identity watchlist — not buy prices", "",
                  "The public feed supplied some grossly inconsistent catalog estimates. They are retained in the machine-readable audit record, NOT shown as actionable prices.",
                  "",
                  "| Player | Identified card and grade | Catalog price | Verified matching sale median | Verified sales | Status | Why not a buy |",
                  "|---|---|---|---:|---:|---|---|"]
        for p in data["players"]:
            for c in p["checks"]:
                reasons = "; ".join(c["reasons"]) or "Meets filters; daily limit/ranking may apply"
                lines.append(f"| {_clean(p['name'])} | {_clean(c['card'])} | **UNVERIFIED — HIDDEN** | {_money(c['sold_median_usd'])} | {_clean(c['sold_comps'])} | {_clean(c['decision'])} | {_clean(reasons)} |")
        lines += ["", "## Player skill-change explanations", ""]
        for p in data["players"]:
            if p["reason"]:
                lines.append(f"- **{_clean(p['name'])}:** {_clean(p['reason'])}")
        if discovery:
            lines += ["", "**Why it isn't a buy:** the bot has measured early MiLB skill changes, "
                      "but cannot yet verify card-specific collector attention and an "
                      "affordable active purchase price. No fabricated trades."]
    lines += ["", "---", "Not a guarantee of profits. No catalog guide value is a real offer. Scores are NOT probabilities. Card-collector interest is NOT measured. No NBA/NFL discovery in this version.", ""]
    return "\n".join(lines)

def save_scouting_report(data, json_path=DEFAULT_SCOUTING_JSON, md_path=DEFAULT_DASHBOARD):
    for target in (Path(json_path), Path(md_path)):
        target.parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path(md_path).write_text(to_markdown(data), encoding="utf-8")
