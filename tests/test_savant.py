"""Tests for the Statcast breakout engine (parsing + scoring + player-first flow).

Verified against a saved Savant CSV fixture so it runs offline.
"""

import os

import pytest

from prehype.breakouts import add_prices, find_breakouts
from prehype.sources.ebay import CompsBackend, EbayCompsClient, SoldComp
from prehype.sources.savant import (
    breakout_score,
    parse_expected_stats,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "savant_expected_sample.csv")


def _batters():
    with open(FIXTURE, encoding="utf-8") as f:
        return parse_expected_stats(f.read(), 2024)


def test_parse_reads_names_and_stats():
    batters = _batters()
    assert len(batters) == 5
    spring = next(b for b in batters if b.player_id == "900001")
    assert spring.name == "Spring Coiled"       # "Coiled, Spring" -> "Spring Coiled"
    assert spring.est_woba == 0.400
    assert spring.woba == 0.310


def test_luck_gap_sign():
    batters = {b.player_id: b for b in _batters()}
    # actual - expected: negative == unlucky (results lag contact)
    assert batters["900001"].luck_gap < 0   # coiled spring, unlucky
    assert batters["900003"].luck_gap > 0   # fluke, overperforming


def test_breakout_score_ranks_unlucky_elite_above_fluke_and_average():
    b = {x.player_id: x for x in _batters()}
    spring = breakout_score(b["900001"])   # elite contact + unlucky
    fluke = breakout_score(b["900003"])    # mediocre contact, lucky
    joe = breakout_score(b["900004"])      # average
    assert spring > fluke
    assert spring > joe
    assert spring >= 80     # elite contact + unlucky should score very high


def test_find_breakouts_respects_min_pa_and_ranks():
    hits = find_breakouts(batters=_batters(), min_pa=150, top=10, min_score=0.0)
    ids = [h.batter.player_id for h in hits]
    assert "900005" not in ids            # 80 PA filtered out by min_pa
    assert hits[0].batter.player_id == "900001"   # coiled spring ranks first


class _FakeEbay(CompsBackend):
    def sold_comps(self, query, *, max_results=240):
        from datetime import date
        return [SoldComp(price=25.0, sold_on=date(2024, 3, 10), title=query)]


def test_add_prices_fills_shortlist_only():
    hits = find_breakouts(batters=_batters(), min_pa=150, top=2, min_score=0.0)
    client = EbayCompsClient(backend=_FakeEbay(), cache_dir="/tmp/prehype-test-cache")
    priced = add_prices(hits, client=client)
    assert all(h.median_price == 25.0 for h in priced)
    assert all(h.comp_count == 1 for h in priced)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
