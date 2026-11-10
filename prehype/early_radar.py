"""PRE-HYPE radar: raw minor-league skill CHANGE before major-league headlines.

No articles, rankings or catalog prices are used for player discovery.
We compare the most recent and immediately preceding 14 MiLB GAMES at the
same team/level. K%, BB% and ISO are independent skills; season OPS only
chooses which player logs are affordable to download, never the final ranking.

This is an *uncalibrated candidate detector*, not a profit probability.
Card collector demand and actual card affordability are separate, unverified
questions. Nothing here authorizes a paper purchase.
"""
from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from statistics import median

from prehype.sources.milb import LEVELS, MilbBatter, fetch_level

GAMES_PER_WINDOW = 14
MIN_GAMES_PER_WINDOW = 10
MIN_PA_PER_WINDOW = 35
MAX_PLAYERS_FOR_LOGS = 88
MAX_WORKERS = 8
MIN_SEASON_PA = 110
MAX_AGE = {"A": 22, "A+": 23, "AA": 24, "AAA": 25}
LEVEL_ORDER = {"A": 1, "A+": 2, "AA": 3, "AAA": 4}
MLB_STATS_URL = "https://statsapi.mlb.com/api/v1/stats"
PLAYER_LOG_BASE = "https://statsapi.mlb.com/api/v1/people/"
HEADERS = {"Accept": "application/json",
           "User-Agent": "CardMarket-PreHypeResearch/1.0"}


def clamp(x, lo=0., hi=1.):
    return min(hi, max(lo, float(x)))


def _request(url, timeout=17):
    if not url.startswith("https://statsapi.mlb.com/api/v1/"):
        raise ValueError("Only official MLB public JSON endpoints")
    try:
        request = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def _integer(v, default=0):
    try:
        return int(v)
    except (ValueError, TypeError, OverflowError):
        return default


def _float(v, default=0.0):
    try:
        f = float(v)
        return f if math.isfinite(f) else default
    except (ValueError, TypeError, OverflowError):
        return default


def _date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def exposed_mlb_ids(year, loader=_request):
    """Conservative exclusion: 100+ MLB PA in same season = not pre-MLB.

    Also return source-quality state. A source outage is not evidence that
    MLB experience is zero: caller must not assert a name is pre-MLB.
    """
    url = MLB_STATS_URL + "?" + urllib.parse.urlencode({
        "stats": "season", "group": "hitting", "season": year,
        "sportId": 1, "gameType": "R", "playerPool": "ALL", "limit": 2000,
    })
    data = loader(url)
    if not isinstance(data, dict):
        return set(), False
    rows = ((data.get("stats") or [{}])[0].get("splits") or [])
    result=set()
    for row in rows:
        if _integer((row.get("stat") or {}).get("plateAppearances")) >= 100:
            pid=(row.get("player") or {}).get("id")
            if pid is not None:
                result.add(str(pid))
    return result, True


def load_game_logs(pid, year, loader=_request):
    pid = str(pid)
    if not pid.isdigit():
        return []
    url = (PLAYER_LOG_BASE + pid + "/stats?" + urllib.parse.urlencode({
        "stats": "gameLog", "group": "hitting", "season": year,
        "leagueListId": "milb_all", "gameType": "R",
        "hydrate": "team(league)",
    }))
    data = loader(url)
    if not isinstance(data, dict):
        return []
    logs=[]
    for group in data.get("stats") or []:
        for row in group.get("splits") or []:
            stats=row.get("stat") or {}
            played=_date(row.get("date"))
            if played is None or played.year != int(year):
                continue
            pa=_integer(stats.get("plateAppearances"))
            if pa <= 0:
                continue
            level = (row.get("team") or {}).get("id")
            logs.append({
                "date":played.isoformat(), "game":(row.get("game") or {}).get("gamePk"),
                "team":str(level) if level is not None else "",
                "pa":pa, "ab":_integer(stats.get("atBats")),
                "h":_integer(stats.get("hits")),
                "dbl":_integer(stats.get("doubles")),
                "trp":_integer(stats.get("triples")),
                "hr":_integer(stats.get("homeRuns")),
                "bb":_integer(stats.get("baseOnBalls")),
                "k":_integer(stats.get("strikeOuts")),
                "hbp":_integer(stats.get("hitByPitch")),
                "sf":_integer(stats.get("sacFlies")),
            })
    # Dedupe retries/double-inclusions by the actual game ID when present.
    unique={}
    for row in logs:
        key=(row["date"], row["game"] or json.dumps(row,sort_keys=True))
        unique[key]=row
    return sorted(unique.values(),key=lambda r:(r["date"], str(r["game"])))


def summarize(logs):
    totals={k:sum(row[k] for row in logs) for k in
            ("pa","ab","h","dbl","trp","hr","bb","k","hbp","sf")}
    pa=totals["pa"]
    ab=totals["ab"]
    singles=totals["h"]-totals["dbl"]-totals["trp"]-totals["hr"]
    bases=singles+2*totals["dbl"]+3*totals["trp"]+4*totals["hr"]
    iso=(bases-totals["h"])/ab if ab else 0
    return {
        "games":len(logs), "pa":pa,
        "k_pct":totals["k"]/pa if pa else None,
        "bb_pct":totals["bb"]/pa if pa else None,
        "iso":iso if ab and singles>=0 else None,
        "hr":totals["hr"],
    }


def change_signal(batter, logs, as_of):
    """Return independent leading changes, or a transparent insufficiency."""
    logs=[row for row in logs if _date(row.get("date")) and
          _date(row["date"])<=as_of and _integer(row.get("pa"))>0]
    logs=sorted(logs,key=lambda r:(r["date"],str(r.get("game"))))
    if len(logs)<2*MIN_GAMES_PER_WINDOW:
        return None
    recent=logs[-GAMES_PER_WINDOW:]
    earlier=logs[-2*GAMES_PER_WINDOW:-GAMES_PER_WINDOW]
    if len(earlier)<MIN_GAMES_PER_WINDOW or len(recent)<MIN_GAMES_PER_WINDOW:
        return None

    # Strict no-cross-promotion comparison: team changes can alter opposing
    # pitching quality, park and usage, so never call that a skill jump.
    teams={r.get("team") for r in recent+earlier if r.get("team")}
    if len(teams)>1:
        return None
    old=summarize(earlier)
    new=summarize(recent)
    if min(old["pa"],new["pa"])<MIN_PA_PER_WINDOW:
        return None
    if any(old[k] is None or new[k] is None for k in ("k_pct","bb_pct","iso")):
        return None

    k_drop=old["k_pct"]-new["k_pct"]
    bb_rise=new["bb_pct"]-old["bb_pct"]
    iso_rise=new["iso"]-old["iso"]
    improving=sum([k_drop>=0.025, bb_rise>=0.015, iso_rise>=0.055])
    # Require TWO leading indicators rather than an isolated hot OPS/HR burst.
    if improving<2 or new["k_pct"]>0.32 or new["iso"]<0.095:
        return None

    # Heuristic strength, explicitly NOT an estimated probability.
    k_part=clamp(k_drop/0.10)
    bb_part=clamp(bb_rise/0.07)
    iso_part=clamp(iso_rise/0.16)
    trend=0.42*k_part+0.28*bb_part+0.30*iso_part
    # Shrink small samples; do not report a 14-game jump as a proven talent
    # level. This discount is a ranking guard, not a posterior calibration.
    coverage=clamp(min(old["pa"],new["pa"])/80)
    age_limit=MAX_AGE.get(batter.level,23)
    if batter.age is None:
        age_factor=.80
    elif batter.age<=age_limit-2:
        age_factor=1.
    elif batter.age<=age_limit:
        age_factor=.90
    else:
        age_factor=.55
    score=round(100*(.25+.75*trend)*(.60+.40*coverage)*age_factor,1)
    last_game=_date(recent[-1]["date"])
    age_days=(as_of-last_game).days
    phase="OFFSEASON_REVIEW" if age_days>30 else "IN_SEASON_SIGNAL"
    reason=(
        f"{batter.level}, age {batter.age if batter.age is not None else '?'}: "
        f"two 14-game samples ({old['pa']} vs {new['pa']} PA); "
        f"K% {old['k_pct']:.1%}→{new['k_pct']:.1%}, "
        f"BB% {old['bb_pct']:.1%}→{new['bb_pct']:.1%}, "
        f"ISO {old['iso']:.3f}→{new['iso']:.3f}. "
        f"Last game {last_game.isoformat()}. "
        "Collector interest and card price NOT validated."
    )
    return {
        "score":score, "reason":reason, "last_game":last_game.isoformat(),
        "phase":phase,
        "old":old, "new":new,
        "k_delta":round(-k_drop,4),
        "bb_delta":round(bb_rise,4),
        "iso_delta":round(iso_rise,4),
        "sample_warning":"Two small recent samples; signal not backtested or calibrated",
    }


def choose_log_candidates(batters, exposed_ids, *, max_n=MAX_PLAYERS_FOR_LOGS):
    # Dedupe players promoted between MiLB levels; keep most advanced level
    # with enough age-appropriate PA, do NOT discover stars from news lists.
    by_id={}
    for player in batters:
        if player.pa<MIN_SEASON_PA or player.age is None:
            continue
        if player.age>MAX_AGE.get(player.level,23) or player.k_rate>.35:
            continue
        if str(player.player_id) in exposed_ids:
            continue
        current=by_id.get(player.player_id)
        if current is None or LEVEL_ORDER.get(player.level,0)>LEVEL_ORDER.get(current.level,0):
            by_id[player.player_id]=player
    def priority(p):
        typical=next((v[1] for v in LEVELS.values() if v[0]==p.level),22)
        age_advantage=max(0,typical-p.age)
        # Mature full-season performance is not the final ranking and not an
        # edge: use only to choose a balanced sample to request game logs.
        onbase=max(0,p.bb_rate-p.k_rate*.12)
        return (min(3,age_advantage)*.38 + onbase*3 +
                clamp((p.ops-.670)/.350)*.45 +
                clamp(p.pa/350)*.14)
    ranked=sorted(by_id.values(),key=lambda p:(-priority(p),p.player_id))
    return ranked[:max_n]


def scan_early_prospects(*,year=None,as_of=None,level_fetch=fetch_level,
                         logs_fetch=load_game_logs, exposure_fetch=exposed_mlb_ids,
                         max_logs=MAX_PLAYERS_FOR_LOGS):
    as_of=as_of or date.today()
    year=year or as_of.year
    batters=[]
    missing=[]
    for level in LEVELS:
        rows=level_fetch(year,level)
        if not rows:
            missing.append(LEVELS[level][0])
        else:
            batters.extend(rows)
    exposed, exposure_ok=exposure_fetch(year)
    # If exposure coverage is missing, you may still create a watchlist, but
    # cannot call candidates pre-MLB or pre-hype.
    eligible=choose_log_candidates(batters,exposed,max_n=max_logs)
    signal_rows=[]
    logs_with_data=0
    if eligible:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures={pool.submit(logs_fetch,p.player_id,year):p for p in eligible}
            for task in as_completed(futures):
                p=futures[task]
                try:
                    logs=task.result()
                except Exception:
                    logs=[]
                if logs:
                    logs_with_data+=1
                signal=change_signal(p,logs,as_of)
                if not signal:
                    continue
                # Scores are 0-100 HEURISTIC evidence grades, NOT probabilities.
                signal_rows.append({
                    "name":p.name,"playerId":p.player_id,
                    "position":"BAT","level":p.level,"age":p.age,
                    "breakoutScore":signal["score"],"dealScore":None,
                    "sleeperScore":None,"hypePct":None,
                    "searchInterestVsJudgePct":None,
                    "cardHypeVerified":False,
                    "marketExposure":"UNKNOWN — NOT VERIFIED QUIET",
                    "priceTrend":None, "cards":{},
                    "kind":"MiLB 14-game skill change",
                    "reason":signal["reason"],
                    "earlySignal":signal,
                    "discoverySource":"MLB StatsAPI MiLB official game logs",
                    "timeContext":signal["phase"],
                    "mlbExposureDataOK":exposure_ok,
                })
    signal_rows.sort(key=lambda c:(-c["breakoutScore"],c["name"]))
    audit={
        "pipeline":"PRE_HYPE_MILB_CHANGE_DETECTOR_V1",
        "season":year,"as_of":as_of.isoformat(),
        "offseason":as_of.month in (11,12,1,2),
        "minor_league_levels_available":[LEVELS[k][0] for k in LEVELS
                                          if LEVELS[k][0] not in missing],
        "minor_league_levels_missing":missing,
        "exposure_filter_source_available":exposure_ok,
        "season_stat_rows":len(batters),
        "eligible_for_log_sampling":len(eligible),
        "game_log_records_available_for_players":logs_with_data,
        "independent_skill_changes_found":len(signal_rows),
        "notes":"MiLB game-log K%, BB%, ISO window-to-window; no articles or player popularity used in discovery. Offseason means previous season evidence, NOT fresh in-week signal. No collector hype or card price verified.",
    }
    return signal_rows,audit


if __name__=="__main__":
    rows,diagnostics=scan_early_prospects()
    print(json.dumps(diagnostics,indent=2))
    for c in rows[:15]:
        print(c["name"],c["breakoutScore"],c["reason"])
