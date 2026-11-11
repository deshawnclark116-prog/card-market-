"""PRE-HYPE radar: raw minor-league skill CHANGE before major-league headlines.

No articles, rankings or catalog prices are used for player discovery.
We compare 14v14, 28v28, and 42v42 non-overlapping GAME windows
(28/56/84 games of evidence), always within the same team stint.
K%, BB%, ISO are distinct but correlated indicators. Longer horizons measure
persistence rather than automatically treating a short spike as real.
Season OPS only preselects which raw game logs to download.

This is an *uncalibrated candidate detector*, not a profit probability.
Card collector demand and actual card affordability are separate, unverified
questions. Nothing here authorizes a paper purchase.
"""
from __future__ import annotations

import json
import hashlib
import math
import random
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from statistics import median

from prehype.sources.milb import LEVELS, MilbBatter, fetch_level
from prehype.sources.public_visibility import public_top100_flags, RANKING_URL

GAMES_PER_WINDOW = 14
CONFIRMATION_WINDOWS = (14, 28, 42)
MIN_GAMES_PER_WINDOW = 10
MIN_PA_PER_WINDOW = 35
ISO_BOOTSTRAP_REPS = 192
EVIDENCE_THRESHOLD = 0.75
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
    stats_blocks=data.get("stats")
    if not isinstance(stats_blocks,list) or not stats_blocks:
        return set(), False
    rows = (stats_blocks[0].get("splits") or [])
    # An empty 2026 MLB season feed is not proof everyone has zero MLB PA.
    if not rows:
        return set(), False
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


def _beta_direction_probability(success_old, n_old, success_new, n_new,
                                *, prior_success, prior_failure, lower_is_better):
    """Approximate probability of an *observed rate shift*, not a forecast.

    Independent beta posteriors with explicitly weak fixed smoothing;
    normal approximation to their difference. None of this is calibrated
    to the event 'player will break out' or to card-price appreciation.
    """
    def moments(k, n):
        a, b = k + prior_success, n-k + prior_failure
        total = a+b
        return a/total, a*b / (total*total*(total+1))
    p0, v0 = moments(success_old, n_old)
    p1, v1 = moments(success_new, n_new)
    sd = math.sqrt(v0+v1)
    delta = p0-p1 if lower_is_better else p1-p0
    if sd <= 0:
        return 0.5
    return round(clamp(0.5*(1+math.erf(delta/(sd*math.sqrt(2))))), 3)


def _iso_resample_probability(earlier, recent, *, seed):
    """Deterministic GAME bootstrap; protects against a few big-hit games.

    A bootstrap probability supports the DIRECTION of the current sample
    only. It is not a probability of FUTURE power or card investment returns.
    """
    rng = random.Random(seed)
    def iso_sample(rows):
        ab = xbh = 0
        for _ in range(len(rows)):
            r = rows[rng.randrange(len(rows))]
            ab += r["ab"]
            xbh += r["dbl"] + 2*r["trp"] + 3*r["hr"]
        return xbh / ab if ab > 0 else 0.
    beats = 0
    for _ in range(ISO_BOOTSTRAP_REPS):
        if iso_sample(recent) > iso_sample(earlier):
            beats += 1
    return round(beats/ISO_BOOTSTRAP_REPS, 3)


def compare_window(logs, games, *, player_id=""):
    """Compare disjoint last N games vs the immediately preceding N games.

    Each horizon uses no future games. Longer *nested* horizons overlap the
    14-game horizon, so their statistics must not be multiplied together or
    described as independent out-of-sample confirmation.
    """
    if len(logs) < games*2:
        return {"status":"INSUFFICIENT_GAMES","games_per_window":games,
                "games_available":len(logs)}
    old_games = logs[-2*games:-games]
    new_games = logs[-games:]
    teams = [r.get("team") for r in old_games+new_games]
    if any(not t for t in teams):
        return {"status":"TEAM_ID_MISSING","games_per_window":games}
    if len(set(teams)) != 1:
        return {"status":"TEAM_CHANGE","games_per_window":games}
    old, new = summarize(old_games), summarize(new_games)
    pa_floor = max(MIN_PA_PER_WINDOW, int(2.5*games))
    if min(old["pa"],new["pa"]) < pa_floor:
        return {"status":"LOW_PA","games_per_window":games,
                "old_pa":old["pa"],"new_pa":new["pa"],"min_pa":pa_floor}
    if any(old[k] is None or new[k] is None for k in ("k_pct","bb_pct","iso")):
        return {"status":"STAT_MISSING","games_per_window":games}
    dk = new["k_pct"] - old["k_pct"]
    db = new["bb_pct"] - old["bb_pct"]
    di = new["iso"] - old["iso"]
    improved = {
        "K": dk <= -.025,
        "BB": db >= .015,
        "ISO": di >= .055,
    }
    stable_seed = int.from_bytes(hashlib.sha256(
        (str(player_id)+"|"+str(games)+"|"+str(new_games[-1]["date"])).encode()
    ).digest()[:8],"big")
    posteriors = {
        "K":_beta_direction_probability(
            old["k_pct"]*old["pa"],old["pa"],
            new["k_pct"]*new["pa"],new["pa"],
            prior_success=2,prior_failure=8,lower_is_better=True),
        "BB":_beta_direction_probability(
            old["bb_pct"]*old["pa"],old["pa"],
            new["bb_pct"]*new["pa"],new["pa"],
            prior_success=1,prior_failure=9,lower_is_better=False),
        "ISO":_iso_resample_probability(old_games,new_games,seed=stable_seed),
    }
    supported = [name for name,flag in improved.items()
                 if flag and posteriors[name] >= EVIDENCE_THRESHOLD]
    return {
        "status":"AVAILABLE",
        "games_per_window":games,"old":old,"new":new,
        "team":teams[0],
        "delta":{"K":round(dk,4),"BB":round(db,4),"ISO":round(di,4)},
        "observed_improvements":[name for name,v in improved.items() if v],
        "direction_support":posteriors,
        "supporting_metrics":supported,
        "positive_metric_count":len(improved) and sum(improved.values()),
        "supported_metric_count":len(supported),
        "confirmed":len(supported)>=2,
        "start_date":old_games[0]["date"],
        "last_date":new_games[-1]["date"],
        "note":"Nested, overlapping horizons; direction support is descriptive, NOT a calibrated future-breakout probability.",
    }


EVIDENCE_TIERS = {
    "SUSTAINED_ACROSS_14_28_42":3,
    "BUILDING_14_AND_28":2,
    "EARLY_14_ONLY":1,
    "SHORT_SPIKE_NOT_CONFIRMED":0,
    "LONG_HORIZON_CONFLICT":0,
}


def change_signal(batter, logs, as_of):
    """Flag incipient skill change, then grade persistence on up to 84 games.

    A 14/14 shift makes a WATCH candidate, not a declaration of true talent.
    Requiring longer samples to exist before displaying early candidates
    would cause the system to miss the very first detectable changes.
    """
    logs=[row for row in logs if _date(row.get("date")) and
          _date(row["date"])<=as_of and _integer(row.get("pa"))>0]
    logs=sorted(logs,key=lambda r:(r["date"],str(r.get("game"))))
    comparisons={str(g):compare_window(logs,g,player_id=batter.player_id)
                 for g in CONFIRMATION_WINDOWS}
    short = comparisons["14"]
    if short["status"] != "AVAILABLE":
        return None
    old, new = short["old"], short["new"]
    if (short["positive_metric_count"]<2
            or new["k_pct"]>.32 or new["iso"]<.095):
        return None

    medium = comparisons["28"]
    long = comparisons["42"]
    if medium["status"]=="AVAILABLE" and not medium["confirmed"]:
        tier="SHORT_SPIKE_NOT_CONFIRMED"
    elif medium["status"]=="AVAILABLE" and medium["confirmed"]:
        if long["status"]=="AVAILABLE" and not long["confirmed"]:
            tier="LONG_HORIZON_CONFLICT"
        elif long["status"]=="AVAILABLE" and long["confirmed"]:
            tier="SUSTAINED_ACROSS_14_28_42"
        else:
            tier="BUILDING_14_AND_28"
    else:
        tier="EARLY_14_ONLY"

    # A short-term jump without consistent evidence across 28/42 games has
    # a deliberately LOWER ranking, even with an impressive recent ISO.
    dk = -short["delta"]["K"]
    db = short["delta"]["BB"]
    di = short["delta"]["ISO"]
    trend=(.42*clamp(dk/.10) + .28*clamp(db/.07) +
           .30*clamp(di/.16))
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
    # Shared time-window grades are HEURISTIC, NOT calibrated probabilities.
    base=100*(.25+.75*trend)*(.60+.40*coverage)*age_factor
    multiplier={
        "SUSTAINED_ACROSS_14_28_42":1.08,
        "BUILDING_14_AND_28":1.0,
        "EARLY_14_ONLY":.80,
        "SHORT_SPIKE_NOT_CONFIRMED":.58,
        "LONG_HORIZON_CONFLICT":.65,
    }[tier]
    score=round(min(100,base*multiplier),1)
    last_game = _date(short["last_date"])
    phase="OFFSEASON_REVIEW" if (as_of-last_game).days>30 else "IN_SEASON_SIGNAL"
    last_horizon = max((int(g) for g,v in comparisons.items()
                        if v["status"]=="AVAILABLE"),default=14)
    # Contradictions should be visible, not silently omitted.
    tail = (
        "Persistent across the measured 14/28/42 horizons"
        if tier=="SUSTAINED_ACROSS_14_28_42" else
        "The 14- and 28-game trends both have supporting signals"
        if tier=="BUILDING_14_AND_28" else
        "Longer-window evidence conflicts with a shorter improvement"
        if tier=="LONG_HORIZON_CONFLICT" else
        "Recent improvement is NOT confirmed by the 28-game comparison"
        if tier=="SHORT_SPIKE_NOT_CONFIRMED" else
        "Only the short horizon is testable; NOT yet confirmed"
    )
    reason=(
        f"{batter.level}, age {batter.age if batter.age is not None else '?'}: "
        f"14v14 K% {old['k_pct']:.1%}→{new['k_pct']:.1%}, "
        f"BB% {old['bb_pct']:.1%}→{new['bb_pct']:.1%}, "
        f"ISO {old['iso']:.3f}→{new['iso']:.3f}; "
        f"{tail}. Up to {last_horizon*2} same-team games assessed. "
        f"Last game {last_game.isoformat()}. "
        "Collector interest and card price NOT validated."
    )
    return {
        "score":score, "reason":reason,"last_game":last_game.isoformat(),
        "phase":phase,"evidence_tier":tier,
        "evidence_tier_order":EVIDENCE_TIERS[tier],
        "comparisons":comparisons,
        "games_in_history":len(logs),
        "max_comparison_games":last_horizon*2,
        "old":old,"new":new,
        "k_delta":round(short["delta"]["K"],4),
        "bb_delta":round(db,4),
        "iso_delta":round(di,4),
        "sample_warning":("Direction-support numbers describe sampled changes only; "
                          "windows overlap; no calibrated future-breakout or persistence probability. "
                          "Offseason data is stale." if phase=="OFFSEASON_REVIEW"
                          else "Direction support is not a future-breakout probability."),
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
                         visibility_fetch=public_top100_flags,
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
    # Full-season histories use exactly the same official player game logs
    # already downloaded for skill discovery: no new provider or API key.
    from prehype.full_season import full_season_trajectory
    signal_rows=[]
    all_profiles=[]
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
                season_path=full_season_trajectory(
                    logs,as_of,player_id=p.player_id)
                all_profiles.append({
                    "player_id":p.player_id,
                    "name":p.name, "age":p.age,
                    "level":p.level,
                    "early_signal_now":False,
                    "trajectory":season_path,
                })
                signal=change_signal(p,logs,as_of)
                if not signal:
                    # Earlier rises and current declines are retained in the
                    # complete audit, even if the old 14v14 late-only filter
                    # would silently omit these players from the current board.
                    continue
                all_profiles[-1]["early_signal_now"]=True
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
                    "kind":"MiLB multi-horizon skill persistence",
                    "reason":signal["reason"],
                    "earlySignal":signal,
                    "seasonTrajectory":season_path,
                    "discoverySource":"MLB StatsAPI MiLB official game logs",
                    "timeContext":signal["phase"],
                    "mlbExposureDataOK":exposure_ok,
                })
    signal_rows.sort(key=lambda c:(
        -(c["earlySignal"].get("evidence_tier_order") or 0),
        -c["breakoutScore"],c["name"]))
    # Rankings are a negative-hype cross-check ONLY. Zero ranked names
    # never means nobody knows the player or his 1st Auto.
    names=[c["name"] for c in signal_rows]
    ranked, rankings_ok=visibility_fetch(names)
    rejected=[]
    for candidate in signal_rows:
        membership=ranked.get(candidate["name"])
        if membership is True:
            candidate["marketExposure"]="PUBLIC TOP-100 PROSPECT — NOT PRE-HYPE"
            rejected.append({"name":candidate["name"],
                             "skill_score":candidate["breakoutScore"],
                             "reason":"Appears on published MLB Pipeline Top-100 aggregation",
                             "source":RANKING_URL})
        elif membership is False:
            candidate["marketExposure"]="NOT ON CHECKED TOP-100 — HOBBY HYPE UNKNOWN"
        else:
            candidate["marketExposure"]="TOP-100 CHECK UNAVAILABLE — HOBBY HYPE UNKNOWN"
    # ALL baseball improvement signals belong in the public research board,
    # even when their cards are unaffordable, they are on a public Top-100
    # prospect ranking, or no first autograph can be verified. Recognition
    # is a separate investment screen, never a reason to hide player evidence.
    all_skill_improvement_candidates=[]
    for c in sorted(signal_rows,key=lambda c:(-c["breakoutScore"],c["name"])):
        signal=c["earlySignal"]
        short=signal["comparisons"]["14"]
        all_skill_improvement_candidates.append({
            "name":c["name"],"player_id":c["playerId"],
            "age":c["age"],"level":c["level"],
            "games_tracked":signal["games_in_history"],
            "skill_score_not_probability":c["breakoutScore"],
            "evidence_tier":signal["evidence_tier"],
            "full_season_phase":c["seasonTrajectory"]["development_phase"],
            "last_game":signal["last_game"],
            "short_window_before":short.get("old"),
            "short_window_after":short.get("new"),
            "short_window_delta":short.get("delta"),
            "supporting_metrics":short.get("supporting_metrics",[]),
            "public_top100_ranked":ranked.get(c["name"]) is True,
            "public_top100_status":(
                "RANKED" if ranked.get(c["name"]) is True else
                "NOT_RANKED_CHECKED" if ranked.get(c["name"]) is False else
                "UNKNOWN"
            ),
            "collector_hype_verified":False,
            "card_buy_eligible":False,
            "hype_note":("Already publicly ranked" if ranked.get(c["name"]) is True
                         else "Not on checked Top-100; collector hype UNKNOWN"
                         if ranked.get(c["name"]) is False
                         else "Top-100 source unavailable; collector hype UNKNOWN"),
        })
    signal_rows=[c for c in signal_rows if ranked.get(c["name"]) is not True]
    # This report covers EVERY eligible sampled hitter, including hitters
    # whose current 14v14 signal disappeared, worsened, or reversed.
    # It is a research history, NOT a card-buy candidate list.
    all_profiles.sort(key=lambda p:(p["name"].casefold(),p["player_id"]))
    phase_counts={}
    for profile in all_profiles:
        phase=profile["trajectory"]["development_phase"]
        phase_counts[phase]=phase_counts.get(phase,0)+1
    historical=[]
    for profile in all_profiles:
        trajectory=profile["trajectory"]
        if trajectory["first_observed_uptrend"] and trajectory["current_direction"]!="UPTREND":
            historical.append({
                "name":profile["name"],"player_id":profile["player_id"],
                "age":profile["age"],"level":profile["level"],
                "development_phase":trajectory["development_phase"],
                "games_available":trajectory["games_available"],
                "first_observed_uptrend":trajectory["first_observed_uptrend"],
                "last_observed_downtrend":trajectory["last_observed_downtrend"],
                "last_game":trajectory["last_game"],
                "latest_window_status":trajectory["latest_window_status"],
                "early_signal_now":profile["early_signal_now"],
            })
    historical.sort(key=lambda p:(
        0 if p["development_phase"]=="REGRESSING_AFTER_UPTREND" else 1,
        -p["games_available"],p["name"]))
    current_skill_names={p["name"] for p in all_skill_improvement_candidates}
    # A second, looser view catches rising players who did NOT pass the
    # stricter 14v14 + two positive skills gate. Label them separately.
    additional_upward_trajectories=[]
    for profile in all_profiles:
        trajectory=profile["trajectory"]
        if (profile["name"] in current_skill_names
                or trajectory["current_direction"]!="UPTREND"):
            continue
        additional_upward_trajectories.append({
            "name":profile["name"],"player_id":profile["player_id"],
            "age":profile["age"],"level":profile["level"],
            "games_tracked":trajectory["games_available"],
            "full_season_phase":trajectory["development_phase"],
            "last_game":trajectory["last_game"],
            "last_observed_uptrend":trajectory["last_observed_uptrend"],
            "recent_window":trajectory.get("recent_window"),
            "skill_score_not_probability":None,
            "status":"ROLLING_UPTREND_ONLY_DID_NOT_PASS_CORE_EARLY_TRIGGER",
            "card_buy_eligible":False,
        })
    additional_upward_trajectories.sort(key=lambda p:p["name"])
    audit={
        "pipeline":"PRE_HYPE_MILB_FULL_SEASON_TRAJECTORY_V2",
        "season":year,"as_of":as_of.isoformat(),
        "offseason":as_of.month in (11,12,1,2),
        "minor_league_levels_available":[LEVELS[k][0] for k in LEVELS
                                          if LEVELS[k][0] not in missing],
        "minor_league_levels_missing":missing,
        "exposure_filter_source_available":exposure_ok,
        "season_stat_rows":len(batters),
        "eligible_for_log_sampling":len(eligible),
        "game_log_records_available_for_players":logs_with_data,
        "full_season_player_histories":len(all_profiles),
        "total_player_games_recorded":sum(
            p["trajectory"]["games_available"] for p in all_profiles),
        "full_season_phase_counts":phase_counts,
        "historical_uptrend_now_not_rising":historical,
        "full_season_history_path":"data/card_bot_full_season_latest.json",
        "full_season_profiles":all_profiles,
        "independent_skill_changes_found":len(all_skill_improvement_candidates),
        "all_skill_improvement_candidates":all_skill_improvement_candidates,
        "additional_upward_trajectories":additional_upward_trajectories,
        "all_positive_development_names_count":(
            len(all_skill_improvement_candidates)+len(additional_upward_trajectories)),
        "all_skill_evidence_tier_counts":{
            tier:sum(1 for c in all_skill_improvement_candidates
                     if c["evidence_tier"]==tier)
            for tier in EVIDENCE_TIERS
        },
        "windows_per_side_games":list(CONFIRMATION_WINDOWS),
        "max_history_games_compared":2*max(CONFIRMATION_WINDOWS),
        "evidence_tier_counts":{
            tier:sum(1 for c in signal_rows
                     if c["earlySignal"]["evidence_tier"]==tier)
            for tier in EVIDENCE_TIERS
        },
        "prospects_after_recognition_exclusion":len(signal_rows),
        "public_top100_source_available":rankings_ok,
        "public_top100_source":RANKING_URL,
        "already_publicized_excluded":rejected,
        "notes":"ALL available 2026 games tracked for each sampled hitter, with 14-game non-overlapping season blocks, 7-game checkpoints and rolling 7/14/28 snapshots. The existing nested 14v14/28v28/42v42 evidence gates remain. Promotions and >21-day layoffs split comparable stints, not raw history. 2026 offseason is retrospective; no backtest or calibrated prediction; card collector demand and exact price remain unverified.",
    }
    return signal_rows,audit


if __name__=="__main__":
    rows,diagnostics=scan_early_prospects()
    print(json.dumps(diagnostics,indent=2))
    for c in rows[:15]:
        print(c["name"],c["breakoutScore"],c["reason"])
