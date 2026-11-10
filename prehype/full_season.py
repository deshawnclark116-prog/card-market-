"""Chronological, source-only full-season MiLB development history.

This module tracks EVERY available regular-season game for a sampled hitter.
It is not a predictor and does not claim that 14-game patterns are stable.
Stints are separated at team changes, missing team IDs, and >21-day gaps:
no 14-vs-14 comparisons span different MiLB environments or injury gaps.

Checkpoints are generated using only games played by that date. Trends are
descriptive threshold hits, NOT calibrated future breakout probabilities.
"""
from __future__ import annotations

from datetime import date
from prehype.early_radar import _date, _integer, summarize

CHECKPOINT_GAMES = 7
ROLLING_WINDOWS = (7, 14, 28)
BLOCK_GAMES = 14
BASELINE_GAMES = 14
MIN_PA_HALF = 35
MAX_GAP_DAYS = 21
MIN_RECENT_PA = 15
DELTA_CUTOFF = {"K": .025, "BB": .015, "ISO": .055}


def _rounded_stats(rows):
    raw = summarize(rows)
    ab = sum(_integer(r["ab"]) for r in rows)
    hits = sum(_integer(r["h"]) for r in rows)
    bb = sum(_integer(r["bb"]) for r in rows)
    hbp = sum(_integer(r["hbp"]) for r in rows)
    sf = sum(_integer(r["sf"]) for r in rows)
    dbl = sum(_integer(r["dbl"]) for r in rows)
    trp = sum(_integer(r["trp"]) for r in rows)
    hr = sum(_integer(r["hr"]) for r in rows)
    tb = hits + dbl + 2*trp + 3*hr
    obp_den = ab + bb + hbp + sf
    avg = hits/ab if ab else None
    obp = (hits+bb+hbp)/obp_den if obp_den else None
    slg = tb/ab if ab else None
    return {
        "games": len(rows), "pa": raw["pa"], "ab": ab, "hits":hits,
        "bb":bb, "k":sum(_integer(r["k"]) for r in rows),
        "hr":hr, "doubles":dbl,"triples":trp,
        "avg":round(avg,4) if avg is not None else None,
        "obp":round(obp,4) if obp is not None else None,
        "slg":round(slg,4) if slg is not None else None,
        "ops":round(obp+slg,4) if obp is not None and slg is not None else None,
        "iso":round(raw["iso"],4) if raw["iso"] is not None else None,
        "k_pct":round(raw["k_pct"],4) if raw["k_pct"] is not None else None,
        "bb_pct":round(raw["bb_pct"],4) if raw["bb_pct"] is not None else None,
    }


def _pair_direction(earlier, recent):
    """Threshold-based within-stint direction, never a likelihood estimate."""
    before, after = _rounded_stats(earlier), _rounded_stats(recent)
    info = {"status":"AVAILABLE","before":before,"after":after}
    if min(before["pa"], after["pa"]) < MIN_PA_HALF:
        info["status"]="LOW_PA"
        info["direction"]="INSUFFICIENT"
        return info
    if any(before[x] is None or after[x] is None for x in ("k_pct","bb_pct","iso")):
        info["status"]="STAT_MISSING"
        info["direction"]="INSUFFICIENT"
        return info
    delta = {
        "K": round(after["k_pct"] - before["k_pct"],4),
        "BB": round(after["bb_pct"] - before["bb_pct"],4),
        "ISO": round(after["iso"] - before["iso"],4),
    }
    up = [x for x,good in (
        ("K",delta["K"]<=-DELTA_CUTOFF["K"]),
        ("BB",delta["BB"]>=DELTA_CUTOFF["BB"]),
        ("ISO",delta["ISO"]>=DELTA_CUTOFF["ISO"]),
    ) if good]
    down = [x for x,bad in (
        ("K",delta["K"]>=DELTA_CUTOFF["K"]),
        ("BB",delta["BB"]<=-DELTA_CUTOFF["BB"]),
        ("ISO",delta["ISO"]<=-DELTA_CUTOFF["ISO"]),
    ) if bad]
    if len(up)>=2 and len(down)<2:
        direction="UPTREND"
    elif len(down)>=2 and len(up)<2:
        direction="DOWNTREND"
    elif up or down:
        direction="MIXED"
    else:
        direction="FLAT"
    info.update({"direction":direction,"deltas":delta,
                 "up_metrics":up, "down_metrics":down,
                 "method":"2-of-3 raw K/BB/ISO deltas, NOT a probability"})
    return info


def _eligible_rows(logs, as_of):
    rows=[]
    for item in logs:
        played = _date(item.get("date"))
        if played is None or played>as_of or _integer(item.get("pa"))<=0:
            continue
        # Game feed has been deduplicated by load_game_logs. Invalid stats are
        # excluded rather than quietly converted to a seemingly excellent AVG.
        if any(_integer(item.get(k))<0 for k in
               ("pa","ab","h","dbl","trp","hr","bb","k","hbp","sf")):
            continue
        ab,h=_integer(item.get("ab")),_integer(item.get("h"))
        doubles=_integer(item.get("dbl"))
        triples=_integer(item.get("trp"))
        hr=_integer(item.get("hr"))
        if h>ab or doubles+triples+hr>h:
            continue
        row=dict(item)
        row["date"]=played.isoformat()
        row["team"]=str(item.get("team") or "")
        rows.append(row)
    return sorted(rows,key=lambda r:(r["date"],str(r.get("game",""))))


def _split_stints(rows):
    stints=[]
    reasons=[]
    for r in rows:
        if not stints:
            stints.append([r])
            reasons.append("SEASON_START")
            continue
        previous=stints[-1][-1]
        days=(_date(r["date"])-_date(previous["date"])).days
        reason=(
            "MISSING_TEAM_ID" if not r["team"] or not previous["team"] else
            "TEAM_CHANGE" if r["team"] != previous["team"] else
            "LONG_GAP" if days>MAX_GAP_DAYS else
            None
        )
        if reason is not None:
            stints.append([r])
            reasons.append(reason)
        else:
            stints[-1].append(r)
    return stints,reasons


def full_season_trajectory(logs,as_of,*, player_id=None,checkpoint_step=CHECKPOINT_GAMES):
    """Track start-to-finish trajectory without discarding old game windows.

    Each historical checkpoint is computed with rows available ON ITS DATE;
    transitions are descriptive as-of changes, not backfilled predictions.
    """
    if checkpoint_step<1:
        raise ValueError("checkpoint_step must be positive")
    rows=_eligible_rows(logs,as_of)
    stints,reasons=_split_stints(rows)
    snapshots=[]
    blocks=[]
    stint_views=[]
    all_signals=[]
    for stint_index,(group,reason) in enumerate(zip(stints,reasons),1):
        stint_views.append({
            "stint":stint_index, "team":group[0]["team"] or "UNKNOWN",
            "reason_started":reason,"first_game":group[0]["date"],
            "last_game":group[-1]["date"],"games":len(group),
            "stats":_rounded_stats(group),
        })
        # Non-overlapping season segments, including the LAST partial block.
        # Unlike the 84-game detector, no earlier game is discarded.
        for first in range(0,len(group),BLOCK_GAMES):
            segment=group[first:first+BLOCK_GAMES]
            blocks.append({
                "stint":stint_index,"team":group[0]["team"] or "UNKNOWN",
                "game_start":first+1,"game_end":first+len(segment),
                "first_date":segment[0]["date"],
                "last_date":segment[-1]["date"],
                "partial":len(segment)<BLOCK_GAMES,
                "stats":_rounded_stats(segment),
            })
        checkpoints=list(range(checkpoint_step,len(group)+1,checkpoint_step))
        if len(group) not in checkpoints:
            checkpoints.append(len(group))
        for end in checkpoints:
            available=group[:end]
            recent=available[-BASELINE_GAMES:]
            record={
                "stint":stint_index, "team":group[0]["team"] or "UNKNOWN",
                "stint_game":end,"as_of":available[-1]["date"],
                "season_game":sum(len(s) for s in stints[:stint_index-1])+end,
                "cum_stint":_rounded_stats(available),
                "cum_season":_rounded_stats(rows[:sum(len(s) for s in stints[:stint_index-1])+end]),
                "rolling":{str(n):_rounded_stats(available[-n:])
                           for n in ROLLING_WINDOWS if len(available)>=n},
                "direction":"INSUFFICIENT",
                "comparison_status":"INSUFFICIENT_GAMES",
            }
            if len(available)>=2*BASELINE_GAMES and group[0]["team"]:
                comparison=_pair_direction(available[-2*BASELINE_GAMES:-BASELINE_GAMES],
                                           recent)
                record["comparison_status"]=comparison["status"]
                record["direction"]=comparison["direction"]
                record["comparison"]=comparison
                if comparison["status"]=="AVAILABLE":
                    all_signals.append(record)
            elif len(available)>=2*BASELINE_GAMES:
                record["comparison_status"]="TEAM_ID_MISSING"
            snapshots.append(record)

    # Phase events record as-of timestamps and never acquire future evidence.
    events=[]
    previous_direction=None
    previous_stint=None
    for c in snapshots:
        direction=c["direction"]
        if c["stint"]!=previous_stint:
            previous_stint=c["stint"]
            previous_direction=None
        if direction in ("UPTREND","DOWNTREND") and direction!=previous_direction:
            events.append({
                "as_of":c["as_of"],"stint":c["stint"],
                "stint_game":c["stint_game"], "season_game":c["season_game"],
                "direction":direction,
                "deltas":c["comparison"]["deltas"],
                "up_metrics":c["comparison"]["up_metrics"],
                "down_metrics":c["comparison"]["down_metrics"],
                "type":"OBSERVED_WINDOW_DIRECTION_NOT_FUTURE_FORECAST",
            })
        if direction!="INSUFFICIENT":
            previous_direction=direction
    newest=snapshots[-1] if snapshots else None
    current=newest["direction"] if newest else "INSUFFICIENT"
    current_valid=newest is not None and newest["comparison_status"]=="AVAILABLE"
    first_up=next((e for e in events if e["direction"]=="UPTREND"),None)
    last_up=next((e for e in reversed(events) if e["direction"]=="UPTREND"),None)
    last_down=next((e for e in reversed(events) if e["direction"]=="DOWNTREND"),None)
    if current=="UPTREND":
        phase=("REBOUNDING_AFTER_DOWNTREND"
               if last_down and last_up and last_down["as_of"]<last_up["as_of"]
               else "CURRENT_UPTREND")
    elif current=="DOWNTREND":
        phase=("REGRESSING_AFTER_UPTREND"
               if first_up else "CURRENT_DOWNTREND")
    elif first_up and current_valid:
        phase="EARLIER_UPTREND_NOW_MIXED_OR_FLAT"
    elif first_up:
        phase="EARLIER_UPTREND_CURRENT_WINDOW_UNAVAILABLE"
    elif current_valid:
        phase="NO_UPTREND_DETECTED"
    else:
        phase="INSUFFICIENT_RECENT_EVIDENCE"
    return {
        "method":"FULL_SEASON_CHRONOLOGY_V1",
        "as_of":as_of.isoformat(),"player_id":str(player_id or ""),
        "games_available":len(rows),
        "teams_or_stints":len(stints),
        "season":_rounded_stats(rows),
        "game_log":rows,  # Every accepted per-game observation, not just selected windows.
        "first_game":rows[0]["date"] if rows else None,
        "last_game":rows[-1]["date"] if rows else None,
        "stints":stint_views,"season_blocks":blocks,
        "checkpoints":snapshots,"phase_events":events,
        "observed_uptrend_checkpoints":sum(c["direction"]=="UPTREND" for c in snapshots),
        "observed_downtrend_checkpoints":sum(c["direction"]=="DOWNTREND" for c in snapshots),
        "first_observed_uptrend":first_up["as_of"] if first_up else None,
        "last_observed_uptrend":last_up["as_of"] if last_up else None,
        "last_observed_downtrend":last_down["as_of"] if last_down else None,
        "current_direction":current, "development_phase":phase,
        "recent_window":newest["comparison"] if current_valid else None,
        "latest_window_status":newest["comparison_status"] if newest else "NO_GAMES",
        "source_caution":("All available qualifying game logs through as_of; "
                          "history blocks include promotions but comparisons do not cross "
                          "teams/gaps. Changes are descriptive, NOT independently "
                          "validated future-breakout signals or card-price predictions."),
    }
