"""Unit tests: early talent CHANGE is the discovery gate, not season OPS/hype."""
from datetime import date, timedelta
from prehype.sources.milb import MilbBatter
from prehype.early_radar import (
    change_signal, choose_log_candidates, scan_early_prospects,
    summarize, exposed_mlb_ids, load_game_logs,
)

DAY = date(2026, 11, 10)

def batter(name="Unknown Young Hitter",pid="12345",level="AA",age=20,pa=220,ops=.850):
    return MilbBatter(player_id=pid,name=name,level=level,age=age,
                      pa=pa,ops=ops,bb_rate=.12,k_rate=.22,hr=9)

def logs(bad=False,transfer=False):
    result=[]
    for i in range(28):
        recent=i>=14
        day=date(2026,8,1)+timedelta(days=i)
        result.append({
            "date":day.isoformat(),"game":1000+i,
            "team":"44" if transfer and recent else "33",
            "pa":5,"ab":4,
            "h":2 if recent else 1,
            "dbl":1 if recent else 0,
            "trp":0, "hr":0,
            "bb":1, "k":1 if recent else 2,
            "hbp":0,"sf":0,
        })
    return result

def test_recency_windows_detect_two_skill_changes_before_public_hype():
    p=batter()
    row=change_signal(p,logs(),DAY)
    assert row
    assert row["old"]["pa"]==70
    assert row["new"]["pa"]==70
    assert row["k_delta"]<0
    assert row["iso_delta"]>0
    assert row["phase"]=="OFFSEASON_REVIEW"
    assert "K%" in row["reason"] and "ISO" in row["reason"]
    assert "NOT validated" in row["reason"]
    assert 0<row["score"]<=100

def test_no_fake_breakout_on_hot_ops_with_no_improving_skill():
    flat=logs()
    for row in flat[:14]:
        row["h"]=2
        row["dbl"]=1
        row["k"]=1
    assert change_signal(batter(),flat,DAY) is None

def test_no_cross_promotion_comparison_or_tiny_sample():
    assert change_signal(batter(),logs(transfer=True),DAY) is None
    assert change_signal(batter(),logs()[:12],DAY) is None
    small=logs()
    for row in small:
        row["pa"]=2
    assert change_signal(batter(),small,DAY) is None

def test_minor_league_only_and_age_level_bias():
    young=batter(pid="9",level="A",age=19)
    mature=batter(pid="8",level="A",age=27,ops=1.500)
    already_major=batter(pid="7",level="AA",age=21)
    values=choose_log_candidates([young,mature,already_major],{"7"})
    assert [p.player_id for p in values]==["9"]

def test_mlb_source_uncertainty_is_not_false_zero():
    def dead(_):return None
    ids,ok=exposed_mlb_ids(2026,loader=dead)
    assert not ok and not ids
    ids,ok=exposed_mlb_ids(2026,loader=lambda url:{"stats":[]})
    assert not ok and not ids
    def populated(_):
        return {"stats":[{"splits":[
            {"player":{"id":44},"stat":{"plateAppearances":150}},
            {"player":{"id":45},"stat":{"plateAppearances":4}},
        ]}]}
    ids,ok=exposed_mlb_ids(2026,loader=populated)
    assert ok and ids=={"44"}

def test_early_radar_does_not_rank_by_old_mlb_xwoba_or_cards():
    youngster=batter("A Player Nobody Knows","9","AA",20)
    young2=batter("Late to Break Out","10","A+",21)
    popular=batter("Famous MLB Star","11","AAA",24)
    def levels(year,sid):
        return {12:[youngster],13:[young2],11:[popular],14:[]}.get(sid,[])
    def loglookup(pid,year):
        return logs() if pid=="9" else logs(transfer=True)
    rows,diag=scan_early_prospects(as_of=DAY,
                                  level_fetch=levels, logs_fetch=loglookup,
                                  exposure_fetch=lambda year:({"11"},True),
                                  visibility_fetch=lambda names:({n:False for n in names},True),
                                  max_logs=30)
    assert [c["name"] for c in rows]==["A Player Nobody Knows"]
    c=rows[0]
    assert c["hypePct"] is None
    assert not c["cardHypeVerified"]
    assert "HOBBY HYPE UNKNOWN" in c["marketExposure"]
    assert c["dealScore"] is None and not c["cards"]
    assert diag["independent_skill_changes_found"]==1
    assert diag["offseason"]
    assert diag["minor_league_levels_missing"]==["A"]

def test_raw_game_logs_includes_milb_game_date_and_team():
    def loader(url):
        assert "leagueListId=milb_all" in url
        return {"stats":[{"splits":[
            {"date":"2026-07-02","team":{"id":22},"game":{"gamePk":123},
             "stat":{"plateAppearances":5,"atBats":4,"hits":2,
                     "doubles":1,"triples":0,"homeRuns":0,
                     "baseOnBalls":1,"strikeOuts":1}}
        ]}]}
    rows=load_game_logs("999999",2026,loader=loader)
    assert len(rows)==1
    assert rows[0]["team"]=="22"
    assert rows[0]["pa"]==5

def test_insufficient_historical_data_cannot_become_false_pre_hype_claim():
    p=batter()
    rows,diag=scan_early_prospects(as_of=DAY,level_fetch=lambda y,s:[p] if s==12 else [],
            logs_fetch=lambda pid,year:[], exposure_fetch=lambda y:(set(),False),
            visibility_fetch=lambda names:({n:False for n in names},True),max_logs=10)
    assert rows==[]
    assert not diag["exposure_filter_source_available"]
    assert diag["game_log_records_available_for_players"]==0


def test_popular_ranked_player_is_excluded_even_if_skill_change_real():
    a=batter("Famous Ranked Prospect","8","AA",20)
    b=batter("Obscure Raw Prospect","9","AA",19)
    rows,diag=scan_early_prospects(
        as_of=DAY,level_fetch=lambda y,s:[a,b] if s==12 else [],
        logs_fetch=lambda pid,year:logs(),exposure_fetch=lambda y:(set(),True),
        visibility_fetch=lambda names:({n:(n=="Famous Ranked Prospect") for n in names},True),
        max_logs=20)
    assert [c["name"] for c in rows]==["Obscure Raw Prospect"]
    assert diag["already_publicized_excluded"][0]["name"]=="Famous Ranked Prospect"
    assert not rows[0]["cardHypeVerified"]
