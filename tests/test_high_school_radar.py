"""2027 prep radar data-access, chronology and non-hype integrity tests."""
import json
from datetime import date

import pytest

from prehype.high_school_radar import (
    EVENTS, USA_ROSTER, PG_GLOBAL_PUBLIC_EVENT_RECORDS, key, parse_tables, pg_event_roster,
    pg_event_velocities, pg_public_global_event_velocities, render_markdown, run_hs_scan,
    usa_18u_players, write_hs_results,
)

USA_HTML="""
<table>
  <tr><th>#</th><th>NAME</th><th>POSITION</th><th>CLASS</th></tr>
  <tr><td>1</td><td><a>High Profile Arm</a></td><td>RHP</td><td>2027</td></tr>
  <tr><td>2</td><td>Old Graduated</td><td>OF</td><td>2026</td></tr>
</table>
"""
JUNE_ROSTER="""
<table>
<tr><th>Team</th><th>No.</th><th>Players</th><th>Grad</th><th>School</th><th>Pos</th></tr>
<tr><td>2027 Prospect Team</td><td>3</td><td><a>Unheralded Arm</a></td><td>2027</td><td>Example HS</td><td>RHP</td></tr>
<tr><td>2027 Prospect Team</td><td>4</td><td>High Profile Arm</td><td>2027</td><td>Example HS</td><td>RHP</td></tr>
<tr><td>2027 Prospect Team</td><td>5</td><td>Not Draft Class</td><td>2028</td><td>Other HS</td><td>RHP</td></tr>
</table>
"""
OCT_ROSTER="""
<table>
<tr><th>Players</th><th>Grad</th><th>Pos</th></tr>
<tr><td>Unheralded Arm</td><td>2027</td><td>RHP</td></tr>
<tr><td>High Profile Arm</td><td>2027</td><td>RHP</td></tr>
<tr><td>Not Draft Class</td><td>2026</td><td>RHP</td></tr>
</table>
"""
JUNE_VELO="""
<table>
<tr><th>Team</th><th>Players</th><th>Th.</th><th>FB</th></tr>
<tr><td>Scout Team</td><td>Unheralded Arm</td><td>R</td><td>87</td></tr>
<tr><td>Scout Team</td><td>Unheralded Arm</td><td>R</td><td>87</td></tr>
<tr><td>National Club</td><td>High Profile Arm</td><td>R</td><td>93</td></tr>
<tr><td>Other</td><td>Not Draft Class</td><td>R</td><td>95</td></tr>
</table>
"""
OCT_VELO="""
<table>
<tr><th>Players</th><th>FB</th></tr>
<tr><td>Unheralded Arm</td><td>92</td></tr>
<tr><td>High Profile Arm</td><td>94</td></tr>
<tr><td>Unknown Grad Pitcher</td><td>100</td></tr>
<tr><td>Not Draft Class</td><td>103</td></tr>
<tr><td>Invalid Measurement</td><td>150</td></tr>
</table>
"""


def mock_fetch(url):
    if url == USA_ROSTER:
        return USA_HTML
    june,oct=EVENTS
    return {
        june["roster"]:JUNE_ROSTER,
        june["velocities"]:JUNE_VELO,
        oct["roster"]:OCT_ROSTER,
        oct["velocities"]:OCT_VELO,
    }.get(url)


def test_official_roster_grad_year_is_explicit_not_guessed():
    players=usa_18u_players(USA_HTML)
    assert [x["name"] for x in players]==["High Profile Arm"]
    assert players[0]["national_team_2026"] is True
    assert all(x["graduation_year"]==2027 for x in players)


def test_public_pg_roster_and_velocities_are_observations_not_player_class():
    players=pg_event_roster(JUNE_ROSTER,EVENTS[0]["roster"])
    assert {x["name"] for x in players}=={"Unheralded Arm","High Profile Arm"}
    v=pg_event_velocities(JUNE_VELO,EVENTS[0])
    assert len(v)==3
    assert len([r for r in v if r["name"]=="Unheralded Arm"])==1
    assert v[0]["event_end"]=="2026-06-30"
    assert not any(r["name"]=="Unknown Grad Pitcher" for r in v)


def test_two_events_can_show_raw_peak_jump_but_never_label_a_breakout():
    result=run_hs_scan(as_of=date(2026,11,11),fetch=mock_fetch)
    assert result["draft_class"]==2027
    assert result["players_with_verified_2027_graduation"]==2
    assert result["public_event_velocity_measurements"]==4
    assert result["observed_velocity_increases"]==1
    assert result["confirmed_breakout_players"]==0
    assert result["verified_cheap_bowman_first_autos"]==0
    by_name={p["name"]:p for p in result["players"]}
    a=by_name["Unheralded Arm"]
    assert a["fastball_peak_change_mph"]==5
    assert a["measurement_status"]=="OBSERVED_VELOCITY_INCREASE_NOT_CONFIRMED_BREAKOUT"
    assert not a["card_buy_eligible"]
    assert a["market_exposure"]=="COLLECTOR_HYPE_UNKNOWN"
    b=by_name["High Profile Arm"]
    assert b["fastball_peak_change_mph"]==1
    assert b["national_team_2026"]
    assert b["market_exposure"]=="NATIONAL_TEAM_PUBLICLY_RECOGNIZED"
    assert "Unknown Grad Pitcher" not in by_name
    assert "Not Draft Class" not in by_name
    assert "Old Graduated" not in by_name


def test_date_scoped_signal_cannot_use_future_october_showcase():
    result=run_hs_scan(as_of=date(2026,7,4),fetch=mock_fetch)
    assert len(result["players"])==2
    assert result["public_event_velocity_measurements"]==2
    assert result["observed_velocity_increases"]==0
    assert all(p["fastball_peak_change_mph"] is None for p in result["players"])
    assert all(not any(x["event_end"]>"2026-07-04" for x in p["observations"])
               for p in result["players"])


def test_missing_all_sources_is_empty_not_invented_star_list():
    result=run_hs_scan(as_of=date(2026,11,11),fetch=lambda url:None)
    assert result["players"]==[]
    assert result["players_with_verified_2027_graduation"]==0
    assert result["confirmed_breakout_players"]==0
    assert all(not s["available"] for s in result["source_diagnostics"])


def test_missing_pg_roster_blocks_unverified_velocity_names():
    def get(url):
        if url in (EVENTS[0]["roster"],EVENTS[1]["roster"]):
            return None
        return mock_fetch(url)
    result=run_hs_scan(as_of=date(2026,11,11),fetch=get)
    assert [p["name"] for p in result["players"]]==["High Profile Arm"]
    assert result["public_event_velocity_measurements"]==2
    assert result["observed_velocity_increases"]==0


def test_no_hype_derived_from_a_velo_jump_and_no_card_buys(tmp_path):
    result=run_hs_scan(as_of=date(2026,11,11),fetch=mock_fetch)
    path=tmp_path/"data"/"hs.json"
    board=tmp_path/"HS.md"
    write_hs_results(result,json_path=path,md_path=board)
    roundtrip=json.loads(path.read_text())
    assert roundtrip["players_with_verified_2027_graduation"]==2
    md=board.read_text()
    assert "Unheralded Arm" in md
    assert "+5 mph" in md
    assert "NOT CONFIRMED BREAKOUT" in md
    assert "NO PUBLIC" not in md.split("## Source access checks",1)[1].split("## All class",1)[0]
    assert "no price" not in md.lower()
    assert all(p["bowman_first_auto_status"]=="NOT_VERIFIED_OR_NOT_YET_ISSUED"
               for p in roundtrip["players"])


def test_parser_ignores_non_table_data_and_malformed_measurements():
    assert parse_tables("<div>Famous Player</div><table><tr><td>2</td></tr></table>")==[[["2"]]]
    assert key("José  A. Pérez")=="jose a perez"
    assert pg_event_velocities("<table><tr><th>FB</th><th>Players</th></tr>"
       "<tr><td>5</td><td>Too Slow</td></tr>"
       "<tr><td>99</td><td>Valid Arm</td></tr>"
       "<tr><td>145</td><td>Too Fast</td></tr></table>",EVENTS[0])[0]["name"]=="Valid Arm"


GLOBAL_VELO_HTML = """
<table>
<tr><th>Rk</th><th>Player</th><th>FB</th><th>Event</th><th>Commitment</th></tr>
<tr><td>5</td><td>Unheralded Arm</td><td>87</td><td>2026 PG 17U WWBA National Championship</td><td>none</td></tr>
<tr><td>4</td><td>Unheralded Arm</td><td>92</td><td>2026 PG WWBA World Championship</td><td>none</td></tr>
<tr><td>1</td><td>Unknown Grad Pitcher</td><td>101</td><td>2026 PG WWBA World Championship</td><td>none</td></tr>
<tr><td>3</td><td>High Profile Arm</td><td>94</td><td>2026 PG WWBA World Championship</td><td>none</td></tr>
<tr><td>1</td><td>Unknown Event</td><td>95</td><td>Another tournament</td><td>none</td></tr>
</table>
"""


def test_global_public_peak_table_recovers_june_when_direct_table_unavailable():
    matched=pg_public_global_event_velocities(GLOBAL_VELO_HTML)
    assert len(matched)==4
    def getter(url):
        if url==EVENTS[0]["velocities"]:
            return None
        if url==PG_GLOBAL_PUBLIC_EVENT_RECORDS:
            return GLOBAL_VELO_HTML
        return mock_fetch(url)
    result=run_hs_scan(as_of=date(2026,11,11),fetch=getter)
    assert result["players_with_verified_2027_graduation"]==2
    assert result["public_event_velocity_measurements"]==4
    assert result["observed_velocity_increases"]==1
    p=next(x for x in result["players"] if x["name"]=="Unheralded Arm")
    assert p["fastball_peak_change_mph"]==5
    assert p["observations"][0]["source"]==PG_GLOBAL_PUBLIC_EVENT_RECORDS
    assert all(x["name"]!="Unknown Grad Pitcher" for x in result["players"])
    assert any("TOP-ONLY BIAS" in x["purpose"] for x in result["source_diagnostics"])
    assert result["confirmed_breakout_players"]==0


def test_global_leaderboard_never_leaks_future_into_past():
    def getter(url):
        if url==PG_GLOBAL_PUBLIC_EVENT_RECORDS:
            return GLOBAL_VELO_HTML
        return mock_fetch(url)
    result=run_hs_scan(as_of=date(2026,7,4),fetch=getter)
    assert result["public_event_velocity_measurements"]==2
    assert all(p["fastball_peak_change_mph"] is None for p in result["players"])
    assert all(p["national_team_2026"] is False for p in result["players"])
    assert all(o["event_end"]<="2026-07-04"
               for p in result["players"] for o in p["observations"])
