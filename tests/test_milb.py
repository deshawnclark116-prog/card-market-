"""Tests for the minor-league prospect scorer."""

import pytest

from prehype.breakouts import find_prospects
from prehype.sources.milb import MilbBatter, prospect_score


def _mk(pid, level, age, ops, pa=400, bb_rate=0.10, k_rate=0.18, hr=15, name=None):
    return MilbBatter(
        player_id=pid, name=name or pid, level=level, age=age, pa=pa,
        ops=ops, bb_rate=bb_rate, k_rate=k_rate, hr=hr,
    )


def test_young_for_level_outranks_old_org_filler():
    # Same OPS, same level — youth should decide.
    young, kind = prospect_score(_mk("young", "AA", 20, 0.850))
    old, _ = prospect_score(_mk("old", "AA", 25, 0.850))
    assert kind == "prospect"
    assert young > old


def test_higher_level_weighted_above_low_level_same_line():
    aa, _ = prospect_score(_mk("aa", "AA", 21, 0.870))
    lowA, _ = prospect_score(_mk("a", "A", 21, 0.870))
    # A 21yo in AA (young for level) beats a 21yo in Low-A (old for level).
    assert aa > lowA


def test_weak_hitter_scores_low():
    score, _ = prospect_score(_mk("weak", "AA", 24, 0.650))
    assert score < 25


def test_find_prospects_filters_min_pa_and_ranks():
    batters = [
        _mk("stud", "AA", 20, 0.900, pa=400),
        _mk("smallsample", "AA", 19, 0.999, pa=40),   # filtered by min_pa
        _mk("filler", "A", 24, 0.700, pa=400),
    ]
    hits = find_prospects(batters=batters, min_pa=150, top=10, min_score=0.0)
    ids = [h.batter.player_id for h in hits]
    assert "smallsample" not in ids
    assert hits[0].batter.player_id == "stud"
    assert hits[0].pos == "BAT"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
