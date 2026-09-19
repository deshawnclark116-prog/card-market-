"""Tests that pin down the scorer's core behavior.

These encode the strategy as assertions: an early breakout must outrank a
value trap, a late runner, and an injured name — so a regression in the model
fails loudly.
"""

from datetime import date, timedelta

import pytest

from prehype.models import (
    AttentionSeries,
    Candidate,
    PerformanceSeries,
    PriceSeries,
)
from prehype.scoring import score_candidate


def _weekly(values):
    start = date.today() - timedelta(weeks=len(values) - 1)
    return [(start + timedelta(weeks=i), v) for i, v in enumerate(values)]


def _make(name, perf, attn, price, **kw):
    return Candidate(
        player_id=name,
        name=name,
        sport="MLB",
        performance=PerformanceSeries.of(_weekly(perf)),
        attention=AttentionSeries.of(_weekly(attn)),
        price=PriceSeries.of(_weekly(price)),
        **kw,
    )


def test_early_breakout_scores_high_and_is_flagged_early():
    c = _make("early", [40, 48, 56, 65, 74, 82], [12, 13, 14, 15, 16, 18], [8, 8, 9, 8, 9, 10])
    sig = score_candidate(c)
    assert sig.verdict == "EARLY"
    assert sig.score >= 40


def test_value_trap_scores_low():
    # Cheap and quiet but no breakout thesis -> should not be a buy.
    c = _make("trap", [48, 47, 49, 46, 48, 47], [15, 14, 16, 15, 14, 15], [6, 6, 7, 6, 6, 6])
    sig = score_candidate(c)
    assert sig.verdict in {"PASS", "WATCH"}
    assert sig.score < 40


def test_late_runner_flagged_window_closing_or_late():
    c = _make("late", [55, 62, 70, 78, 85, 90], [30, 45, 60, 75, 88, 95], [25, 40, 70, 110, 160, 220])
    sig = score_candidate(c)
    assert sig.verdict in {"WINDOW_CLOSING", "TOO_LATE"}


def test_early_breakout_outranks_a_late_runner():
    early = _make("early", [40, 48, 56, 65, 74, 82], [12, 13, 14, 15, 16, 18], [8, 8, 9, 8, 9, 10])
    late = _make("late", [55, 62, 70, 78, 85, 90], [30, 45, 60, 75, 88, 95], [25, 40, 70, 110, 160, 220])
    assert score_candidate(early).score > score_candidate(late).score


def test_injury_flag_lowers_score():
    healthy = _make("healthy", [50, 58, 66, 74, 80, 86], [12, 13, 14, 15, 16, 18], [10, 10, 11, 10, 11, 12])
    hurt = _make(
        "hurt", [50, 58, 66, 74, 80, 86], [12, 13, 14, 15, 16, 18], [10, 10, 11, 10, 11, 12],
        injury_flag=True,
    )
    assert score_candidate(hurt).score < score_candidate(healthy).score


def test_score_is_bounded():
    c = _make("x", [0, 100], [0, 0], [1, 1])
    sig = score_candidate(c)
    assert 0.0 <= sig.score <= 100.0


def test_alert_render_contains_name_and_score():
    c = _make("Jalen Rooke", [40, 48, 56, 65, 74, 82], [12, 13, 14, 15, 16, 18], [8, 8, 9, 8, 9, 10])
    text = score_candidate(c).as_alert()
    assert "Jalen Rooke" in text
    assert "Pre-Hype Score" in text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
