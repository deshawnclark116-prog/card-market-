"""Full-season scan retains a prospect whose earlier improvement disappeared."""
import json
from datetime import date,timedelta
from prehype.early_radar import scan_early_prospects
from prehype.sources.milb import MilbBatter


def test_prior_breakout_then_decline_remains_in_history_even_if_off_current_board():
    name="Unheralded Retrospective Prospect"
    player=MilbBatter(
        player_id="987123",name=name,level="AA",age=20,
        pa=550,ops=.8,bb_rate=.1,k_rate=.19,hr=10,
    )
    rows=[]
    for block in range(8):
        # First three blocks weak, next four improving, final one regresses.
        good=3<=block<=6
        for game in range(14):
            idx=block*14+game
            d=date(2026,4,1)+timedelta(days=idx)
            rows.append({
                "date":d.isoformat(),"game":600000+idx,"team":"500",
                "pa":6 if good else 4,"ab":4,
                "h":2 if good else 1,
                "dbl":2 if good else 0,
                "trp":0,"hr":0,
                "bb":2 if good else 0,
                "k":0 if good else 2,
                "hbp":0,"sf":0,
            })
    candidates,audit=scan_early_prospects(
        as_of=date(2026,11,10),
        level_fetch=lambda year,sid:[player] if sid==12 else [],
        logs_fetch=lambda pid,year:rows,
        exposure_fetch=lambda year:(set(),True),
        visibility_fetch=lambda names:({n:False for n in names},True),
        max_logs=5,
    )
    assert candidates==[], "Declining player is NOT a current pre-hype buy candidate"
    assert audit["full_season_player_histories"]==1
    assert audit["total_player_games_recorded"]==112
    assert audit["historical_uptrend_now_not_rising"][0]["name"]==name
    assert audit["historical_uptrend_now_not_rising"][0]["development_phase"]=="REGRESSING_AFTER_UPTREND"
    profile=audit["full_season_profiles"][0]
    trajectory=profile["trajectory"]
    assert len(trajectory["game_log"])==112
    assert trajectory["season"]["games"]==112
    assert trajectory["first_observed_uptrend"] is not None
    assert trajectory["last_observed_downtrend"] is not None
    # GitHub's persisted full-season JSON must be plain JSON serializable.
    assert len(json.loads(json.dumps(profile))["trajectory"]["season_blocks"])==8
