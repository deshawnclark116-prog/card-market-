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
from prehype.price_discipline import (
    CHEAP_CARD_MAX_CENTS, CHEAP_ALL_IN_MAX_CENTS, assess_low_entry,
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
    if candidate.get("cardHypeVerified") is not True:
        reasons.append("card-collector hype NOT verified; search ratio is not proof of quiet demand")
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
            metadata=(candidate.get("cards") or {}).get(card,{})
            cheap=assess_low_entry(metadata,quote)
            entry_cents=(int(quote["all_in_ask_cents"])
                         if cheap["low_entry_verified"] else None)
            reasons = list(score_reasons)
            if cheap["status"]!="LOW_ENTRY_COST_VERIFIED_UNDERVALUATION_UNKNOWN":
                reasons.append("Low-entry 1st Bowman auto not verified: "+cheap["status"])
            # A verified low-dollar offer may pass the ACQUISITION screen,
            # but must never be described as an undervalued card or a
            # validated market lag. That warning lives in cheap_entry_screen.
            if not fresh:
                reasons.append("no five independently title-matched recent sales of this EXACT card/grade")
            if not (quote and quote.get("independent_exact_sold_comps_verified") is True):
                reasons.append("verified independent same-card sold comps unavailable")
            if entry_cents is not None and entry_cents > state["cash_cents"]:
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
                "all_in_paper_usd": round(entry_cents/100,2) if entry_cents is not None else None,
                "cheap_entry_screen": cheap,
                "cheap_item_price_usd": cheap["item_price_usd"],
                "cheap_delivered_price_usd": cheap["all_in_price_usd"],
                "cheap_acquisition_verified": cheap["low_entry_verified"],
                "market_lag_verified": False,
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
            # Full raw games and rolling checkpoints live in each player's
            # separate GitHub JSON. Keep board JSON below 1MiB/readable.
            "season_trajectory": ({
                k:v for k,v in candidate["seasonTrajectory"].items()
                if k not in ("game_log","checkpoints")
            } if candidate.get("seasonTrajectory") else None),
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
        "", "**CHEAP ≠ AFFORDABLE:** a $10–$25 card is not a pre-hype bargain merely "
        "because it fits the bankroll. This paper strategy targets individually "
        "verified manufacturer-issued **1st Bowman autographs at $5 or less for "
        "the card and $10 or less delivered**. A genuine low-priced card is "
        "still not necessarily underpriced or unnoticed by collectors.",
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
                  "- Full-season tracking: **every available game** from first to last in a sampled player's season, including earlier streaks, slumps, rebounds and team changes",
                  "- Players with complete development histories: **" + str(discovery.get("full_season_player_histories", 0)) + "**",
                  "- Individual game observations retained: **" + str(discovery.get("total_player_games_recorded", 0)) + "**",
                  "- Compare all-season 14-game blocks plus **rolling 7/14/28-game checkpoints**, saved every seven games and at the last game",
                  "- Separate most recent comparison periods: **14v14, 28v28, 42v42** (up to 84 recent games); those overlapping horizons do not determine the entire seasonal history",
                  "- [**Open the full-season index**](data/card_bot_full_season_latest.json) to find one readable JSON file per player (all games, rolling checkpoints, phase events)",
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
        phases = discovery.get("full_season_phase_counts") or {}
        if phases:
            lines += ["", "### Across the full season: what happened to every analyzed hitter?", "",
                      "These phase counts include **all sampled hitters**, not merely today's top breakout signals. "
                      "A player who rose in June but fell in August remains in the research archive.",
                      "",
                      "| Development phase (descriptive) | Players |",
                      "|---|---:|"]
            for key,amount in sorted(phases.items(),key=lambda x:(-x[1],x[0])):
                lines.append(f"| {_clean(key.replace('_',' '))} | {amount} |")
            lines.append("")
        earlier = discovery.get("historical_uptrend_now_not_rising") or []
        if earlier:
            lines += ["", "### Earlier season improvement that later faded or became unclear", "",
                      "**Research-only:** this is the falling-off / cooling-off detector. These names "
                      "are **NOT** recommended card buys. Disappearing from today's breakout list "
                      "does not mean the earlier improvement never occurred.",
                      "",
                      "| Player | Level | Games tracked | Earlier uptrend first seen | Current phase | Last game |",
                      "|---|---|---:|---|---|---|"]
            for item in earlier[:20]:
                pid=str(item.get("player_id") or "")
                pname=_clean(item["name"])
                if pid.isdigit():
                    pname=f"[{pname}](data/card_bot_season_players/{discovery.get('season')}/{pid}.json)"
                lines.append(
                    f"| {pname} | {_clean(item['level'])} | "
                    f"{item['games_available']} | {_clean(item.get('first_observed_uptrend'))} | "
                    f"{_clean(item.get('development_phase','').replace('_',' '))} | "
                    f"{_clean(item.get('last_game'))} |"
                )
            if len(earlier)>20:
                lines.append(f"More histories ({len(earlier)-20}) are in the full-season JSON.")
            lines.append("")
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
                "| Evidence rank | Player | Level | Age | Games tracked | Full-season phase | Latest persistence tier | Heuristic score | Per-game file |",
                "|---:|---|---|---:|---:|---|---|---:|---|",
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
                trajectory=p.get("season_trajectory") or {}
                player_id=str(p.get("player_id") or "")
                history_link=(f"[Full season](data/card_bot_season_players/"
                              f"{discovery.get('season')}/{player_id}.json)"
                              if player_id.isdigit() else "not available")
                lines.append(
                    f"| {p['rank']} | {_clean(p['name'])} | {_clean(p.get('level'))} | "
                    f"{_clean(p.get('age'))} | {_clean(trajectory.get('games_available'))} | "
                    f"{_clean((trajectory.get('development_phase') or 'UNKNOWN').replace('_',' '))} | "
                    f"{_clean(tier_names.get(tier,tier or 'UNKNOWN'))} | "
                    f"{_clean(p.get('breakout_score_not_probability'))} | {history_link} |"
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
            if any(p.get("season_trajectory") for p in data["players"]):
                lines += [
                    "",
                    "## Full-season progression: 14-game blocks, beginning to end",
                    "",
                    "Each line represents a **separate chronological block** of games. "
                    "The final block may be shorter. Blocks never mix players' "
                    "different teams or long layoffs; the full per-game audit also "
                    "contains rolling 7/14/28-game checkpoints.",
                    "",
                    "| Player | Team stint | Games in stint | Through | PA | AVG | OBP | SLG | ISO | K% | BB% | HR |",
                    "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
                ]
                def f_stat(obj,key,pct=False):
                    val=obj.get(key)
                    if val is None:
                        return "—"
                    return f"{val:.1%}" if pct else f"{val:.3f}"
                for p in data["players"]:
                    for block in (p.get("season_trajectory") or {}).get("season_blocks", []):
                        stats=block["stats"]
                        period=f"{block['game_start']}-{block['game_end']}"
                        if block.get("partial"):
                            period+=" (partial)"
                        lines.append(
                            f"| {_clean(p['name'])} | {block['stint']} / {_clean(block['team'])} | "
                            f"{period} | {_clean(block['last_date'])} | {stats['pa']} | "
                            f"{f_stat(stats,'avg')} | {f_stat(stats,'obp')} | "
                            f"{f_stat(stats,'slg')} | {f_stat(stats,'iso')} | "
                            f"{f_stat(stats,'k_pct',True)} | "
                            f"{f_stat(stats,'bb_pct',True)} | {stats['hr']} |"
                        )
                lines += [
                    "",
                    "### When the rolling game statistics changed direction",
                    "",
                    "Events below are **as-of observations** of a 14v14 comparison "
                    "at the date shown—not predictions made on that date.",
                    "",
                    "| Player | As of | Season game | Observed direction | K% Δ | BB% Δ | ISO Δ |",
                    "|---|---|---:|---|---:|---:|---:|",
                ]
                for p in data["players"]:
                    for event in (p.get("season_trajectory") or {}).get("phase_events", []):
                        changes=event["deltas"]
                        lines.append(
                            f"| {_clean(p['name'])} | {_clean(event['as_of'])} | "
                            f"{event['season_game']} | {_clean(event['direction'])} | "
                            f"{changes['K']:+.1%} | {changes['BB']:+.1%} | "
                            f"{changes['ISO']:+.3f} |"
                        )
                lines += [
                    "",
                    "A sudden jump may still be sampling noise or reflect unmodeled "
                    "opponents, ballparks, fatigue or injuries. The historical timeline "
                    "does not establish future breakout odds or cheap card prices.",
                ]
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
                  "| Player | Identified reference | Advertised all-in | Low-entry status | Catalog mark | Verified same-card sales | Decision |",
                  "|---|---|---:|---|---|---:|---|"]
        for p in data["players"]:
            for c in p["checks"]:
                reasons = "; ".join(c["reasons"]) or "Meets filters; daily limit/ranking may apply"
                lines.append(
                    f"| {_clean(p['name'])} | {_clean(c['card'])} | "
                    f"{_money(c.get('cheap_delivered_price_usd'))} | "
                    f"{_clean(c['cheap_entry_screen']['status'].replace('_',' '))} | "
                    f"**UNVERIFIED — HIDDEN** | {_clean(c['sold_comps'])} | "
                    f"{_clean(c['decision'])} ({_clean(reasons)}) |")
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
