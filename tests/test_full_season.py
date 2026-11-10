"""Full-season evolution: no early/late observations omitted or leaked."""
from datetime import date,timedelta
from prehype.full_season import full_season_trajectory

ASOF=date(2026,11,10)

def make_games(blocks,*,change_team_at=None,long_gap_at=None,one_team="A"):
    """Each block is 14 games of (K, BB, doubles, hits, AB)."""
    rows=[]
    t=date(2026,4,1)
    for ci,(strikeouts,bb,dbl,hits,atbats) in enumerate(blocks):
        for j in range(14):
            ix=ci*14+j
            # Dates strictly increase; optional gap simulates injured-list time.
            day=t+timedelta(days=ix+(30 if long_gap_at is not None and ix>=long_gap_at else 0))
            rows.append({
                "date":day.isoformat(),"game":100000+ix,
                "team":("B" if change_team_at is not None and ix>=change_team_at else one_team),
                "pa":atbats+bb,"ab":atbats,"h":hits,
                "dbl":dbl,"trp":0,"hr":0,
                "bb":bb,"k":strikeouts,"hbp":0,"sf":0,
            })
    return rows

POOR=(2,0,0,1,4)
BETTER=(0,2,2,2,4)
FADE=(2,0,0,1,4)
FLAT=(1,1,1,2,4)


def test_all_126_games_including_first_and_final_games():
    rows=make_games([POOR]*3+[BETTER]*4+[FADE]*2)
    assert len(rows)==126
    evolution=full_season_trajectory(rows,ASOF,player_id="33")
    assert evolution["games_available"]==126
    assert sum(b["stats"]["games"] for b in evolution["season_blocks"])==126
    assert evolution["first_game"]==rows[0]["date"]
    assert evolution["last_game"]==rows[-1]["date"]
    assert evolution["season"]["pa"]==sum(g["pa"] for g in rows)
    assert evolution["checkpoints"][-1]["stint_game"]==126
    assert evolution["checkpoints"][-1]["cum_season"]["games"]==126
    assert evolution["checkpoints"][-1]["rolling"]["28"]["games"]==28


def test_real_development_then_regression_is_visible_not_only_final_84():
    rows=make_games([POOR]*3+[BETTER]*4+[FADE])
    result=full_season_trajectory(rows,ASOF)
    assert result["first_observed_uptrend"] is not None
    assert result["last_observed_downtrend"] is not None
    assert result["observed_uptrend_checkpoints"]>0
    assert result["observed_downtrend_checkpoints"]>0
    assert result["development_phase"]=="REGRESSING_AFTER_UPTREND"
    assert result["current_direction"]=="DOWNTREND"
    assert result["last_observed_downtrend"]>result["first_observed_uptrend"]


def test_current_rising_after_prior_downtrend_is_rebound_not_first_breakout():
    rows=make_games([BETTER]*3+[FADE]*4+[BETTER])
    result=full_season_trajectory(rows,ASOF)
    assert result["last_observed_downtrend"] is not None
    assert result["current_direction"]=="UPTREND"
    assert result["development_phase"]=="REBOUNDING_AFTER_DOWNTREND"


def test_promotion_creates_new_stint_and_no_cross_team_fake_change():
    rows=make_games([POOR]*4+[BETTER]*3,change_team_at=56)
    result=full_season_trajectory(rows,ASOF)
    assert result["teams_or_stints"]==2
    assert result["stints"][1]["reason_started"]=="TEAM_CHANGE"
    assert result["season"]["games"]==98
    assert all(b["team"]==("A" if b["stint"]==1 else "B")
               for b in result["season_blocks"])
    assert result["checkpoints"][-1]["cum_season"]["games"]==98
    # 3 blocks / 42 games on new team: new skill changes only use team B.
    assert all(x["stint"]==2 for x in result["checkpoints"]
               if x["team"]=="B")


def test_layoff_beyond_21_days_is_a_new_stint():
    rows=make_games([POOR]*3+[BETTER]*3,long_gap_at=42)
    result=full_season_trajectory(rows,ASOF)
    assert result["teams_or_stints"]==2
    assert result["stints"][1]["reason_started"]=="LONG_GAP"
    assert result["season"]["games"]==84


def test_asof_cutoff_and_historical_checkpoints_have_no_future_leakage():
    rows=make_games([POOR]*3+[BETTER]*3)
    early=date.fromisoformat(rows[41]["date"])
    a=full_season_trajectory(rows,early)
    b=full_season_trajectory(rows[:42],early)
    assert a==b
    assert a["games_available"]==42
    assert all(c["as_of"]<=early.isoformat() for c in a["checkpoints"])
    assert all(e["as_of"]<=early.isoformat() for e in a["phase_events"])


def test_partial_block_is_accounted_for_not_discarded():
    rows=make_games([POOR]*2)+make_games([FLAT]*1)[:5]
    # A repeated game identity from the synthetic fixture is okay here;
    # unique records are handled by the ingestion source.
    for j,row in enumerate(rows[-5:]):
        row["date"]=(date(2026,5,1)+timedelta(days=j)).isoformat()
        row["game"]=200000+j
    result=full_season_trajectory(rows,ASOF)
    assert result["games_available"]==33
    assert sum(b["stats"]["games"] for b in result["season_blocks"])==33
    assert result["season_blocks"][-1]["partial"]
    assert result["season_blocks"][-1]["stats"]["games"]==5


def test_undetermined_hype_and_prices_are_not_invented_by_stats_module():
    result=full_season_trajectory(make_games([POOR]*2),ASOF)
    assert "market" not in result
    assert "price" not in result
    assert "NOT" in result["source_caution"]
    assert result["observed_uptrend_checkpoints"]==0


def test_pa_weighted_rates_and_real_extra_base_hits():
    rows=make_games([BETTER])
    result=full_season_trajectory(rows,ASOF)
    stats=result["season"]
    assert stats["games"]==14 and stats["pa"]==84
    assert stats["hits"]==28
    assert stats["doubles"]==28
    assert stats["k_pct"]==0
    assert stats["bb_pct"]==round(28/84,4)
    assert stats["iso"]==0.5
    assert stats["slg"]==1.0
    assert stats["avg"]==0.5
