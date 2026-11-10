from datetime import date

from prehype.paper_bot import make_ledger, simulate_day
from prehype.scouting_report import (
    build_scouting_report, save_scouting_report, to_markdown
)

DAY = date(2026, 11, 9)


def candidate(name="Hidden Prospect", deal=73, breakout=80, hype=2, trend=0.01):
    return {
        "name": name, "dealScore": deal, "breakoutScore": breakout,
        "hypePct": hype, "priceTrend": trend,
        "reason": "xwOBA improved while card prices are flat",
        "cards": {"Bowman 1st auto": {"price": 12, "comps": 8}}
    }


def lookup(player, card, day):
    return {"median_cents": 1200, "comps": 8, "last_sale": day.isoformat()}


def test_scouting_board_shows_every_candidate_and_reason():
    state = make_ledger(DAY)
    rows = [candidate(), candidate("Uninteresting", deal=12)]
    data = build_scouting_report(rows, lookup, DAY, state, "WAITING")
    assert data["players_screened"] == 2
    assert [p["name"] for p in data["players"]] == ["Hidden Prospect", "Uninteresting"]
    assert data["players"][0]["checks"][0]["decision"] == "QUALIFIED (not selected today)"
    assert data["players"][1]["checks"][0]["decision"] == "PASS"
    assert "low deal score" in data["players"][1]["checks"][0]["reasons"][0]
    markdown = to_markdown(data)
    assert "Hidden Prospect" in markdown
    assert "Uninteresting" in markdown
    assert "xwOBA improved" in markdown
    assert "USD 12.00" in markdown


def test_scout_board_shows_paper_bought_and_portfolio():
    state = make_ledger(DAY)
    choices = [candidate()]
    run = simulate_day(state, choices, lookup, DAY)
    data = build_scouting_report(choices, lookup, DAY, state, run["status"], run["buys"])
    assert data["players"][0]["checks"][0]["decision"] == "PAPER BOUGHT TODAY"
    assert data["portfolio"]["number_of_paper_buys"] == 1
    assert "PAPER BOUGHT TODAY" in to_markdown(data)


def test_scout_board_flags_missing_comps_and_hype():
    state = make_ledger(DAY)
    def unavailable(*args):
        return None
    data = build_scouting_report([candidate(hype=None, trend=None)],
                                 unavailable, DAY, state, "WAITING")
    row = data["players"][0]["checks"][0]
    assert row["decision"] == "PASS"
    assert row["sold_median_usd"] is None
    assert "hype data missing" in row["reasons"]
    assert "price trend missing" in row["reasons"]
    assert "independently title-matched recent sales" in " ".join(row["reasons"])


def test_scout_board_handles_no_candidates():
    data = build_scouting_report([], lookup, DAY, make_ledger(DAY), "WAITING")
    markdown = to_markdown(data)
    assert data["players_screened"] == 0
    assert "No candidates returned" in markdown


def test_scout_board_writes_json_and_md(tmp_path):
    data = build_scouting_report([candidate()], lookup, DAY, make_ledger(DAY), "WAITING")
    json_file, markdown_file = tmp_path / "data" / "scouts.json", tmp_path / "BOARD.md"
    save_scouting_report(data, json_path=json_file, md_path=markdown_file)
    assert json_file.exists()
    assert markdown_file.exists()
    assert "Hidden Prospect" in markdown_file.read_text()
    assert "Hidden Prospect" in json_file.read_text()
