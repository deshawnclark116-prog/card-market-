"""Research transparency: NEVER hide baseball skill-change names behind card filters."""
from datetime import date, timedelta

from prehype.early_radar import scan_early_prospects
from prehype.paper_bot import make_ledger
from prehype.scouting_report import build_scouting_report, to_markdown
from prehype.sources.milb import MilbBatter

DAY=date(2026,11,10)


def hitter(name,pid):
    return MilbBatter(player_id=pid,name=name,age=20,level="AA",
                      pa=220,ops=.800,bb_rate=.12,k_rate=.22,hr=7)


def game_logs(*,power=True):
    rows=[]
    for i in range(28):
        improved=i>=14
        rows.append({
            "date":(date(2026,8,1)+timedelta(days=i)).isoformat(),
            "game":800000+i,"team":"123",
            "pa":6 if improved else 5,"ab":4,
            "h":2 if power and improved else 1,
            "dbl":1 if power and improved else 0,
            "trp":0,"hr":0,
            "bb":1 if improved else 0,
            "k":1 if improved else 2,
            "hbp":0,"sf":0,
        })
    return rows


def test_all_improving_names_preserved_regardless_of_publicity():
    popular=hitter("Already Famous Prospect","12345")
    obscure=hitter("Unnoticed Prospect","98765")
    candidates, audit=scan_early_prospects(
        as_of=DAY,
        level_fetch=lambda year,level: [popular,obscure] if level==12 else [],
        logs_fetch=lambda pid,year:game_logs(),
        exposure_fetch=lambda year:(set(),True),
        visibility_fetch=lambda names:({name:name==popular.name for name in names},True),
        max_logs=10,
    )
    # The PAPER BUY shortlist excludes famous players, and is unchanged.
    assert [c["name"] for c in candidates]==[obscure.name]
    assert audit["independent_skill_changes_found"]==2
    assert len(audit["all_skill_improvement_candidates"])==2
    assert {c["name"] for c in audit["all_skill_improvement_candidates"]}=={
        popular.name,obscure.name,
    }
    p=next(x for x in audit["all_skill_improvement_candidates"]
           if x["name"]==popular.name)
    assert p["public_top100_ranked"] is True
    assert p["public_top100_status"]=="RANKED"
    assert p["collector_hype_verified"] is False
    assert p["card_buy_eligible"] is False
    assert p["short_window_delta"]["K"] < 0
    assert p["short_window_delta"]["BB"] > 0
    assert p["games_tracked"]==28
    assert audit["already_publicized_excluded"][0]["name"]==popular.name

    board=build_scouting_report(candidates, lambda *args:None,
                               DAY,make_ledger(DAY),"RESEARCH")
    board["discovery"]=audit
    text=to_markdown(board)
    assert "ALL players with current baseball improvement signals" in text
    section=text.split("## ALL players with current baseball improvement signals",1)[1]
    assert "Already Famous Prospect" in section
    assert "Unnoticed Prospect" in section
    assert "data/card_bot_season_players/2026/12345.json" in section
    assert "RANKED — not a quiet-card claim" in section
    assert board["players_screened"]==1  # Market queue stayed filtered.


def test_rising_checkpoint_without_core_early_signal_gets_separate_visibility():
    player=hitter("Upward But Lower ISO","23456")
    candidates, audit=scan_early_prospects(
        as_of=DAY,
        level_fetch=lambda year,level:[player] if level==12 else [],
        logs_fetch=lambda pid,year:game_logs(power=False),
        exposure_fetch=lambda year:(set(),True),
        visibility_fetch=lambda names:({},True),
        max_logs=10,
    )
    assert candidates==[]
    assert audit["independent_skill_changes_found"]==0
    additional=audit["additional_upward_trajectories"]
    assert len(additional)==1
    assert additional[0]["name"]==player.name
    assert additional[0]["full_season_phase"]=="CURRENT_UPTREND"
    assert audit["all_positive_development_names_count"]==1
    board=build_scouting_report([],lambda *args:None,DAY,make_ledger(DAY),"RESEARCH")
    board["discovery"]=audit
    output=to_markdown(board)
    assert "Additional players with an improving rolling trajectory" in output
    assert player.name in output
    assert "did **not** meet the stricter main skill-change trigger" in output


def test_inaccessible_rankings_do_not_mean_verified_unhyped():
    player=hitter("Unknown Ranking Prospect","23456")
    _,audit=scan_early_prospects(
        as_of=DAY,
        level_fetch=lambda year,level:[player] if level==12 else [],
        logs_fetch=lambda pid,year:game_logs(),
        exposure_fetch=lambda year:(set(),True),
        visibility_fetch=lambda names:({},False),
        max_logs=10,
    )
    all_=audit["all_skill_improvement_candidates"]
    assert len(all_)==1
    assert all_[0]["public_top100_status"]=="UNKNOWN"
    assert "source unavailable" in all_[0]["hype_note"]
