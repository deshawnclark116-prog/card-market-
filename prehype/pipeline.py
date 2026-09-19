"""Gather candidates, score them, and surface only the ones worth your money.

This is the "does all the work" layer: point it at one or more data sources and
it hands back a ranked watchlist, filtered so the top of the list is exactly the
alert you want — *dirt cheap, hype hasn't hit, breakout building.*
"""

from __future__ import annotations

from collections.abc import Iterable

from prehype.models import Signal
from prehype.scoring import ScoreWeights, score_candidate
from prehype.sources.base import DataSource

# Verdicts that represent an actual, actionable "get in early" call.
EARLY_VERDICTS = {"EARLY", "WATCH"}


def scan(
    sources: Iterable[DataSource],
    *,
    weights: ScoreWeights | None = None,
    cheap_ref: float = 15.0,
    rich_ref: float = 500.0,
    min_score: float = 0.0,
    only_early: bool = False,
) -> list[Signal]:
    """Run every source, score every candidate, return signals sorted best-first.

    ``only_early`` keeps just the "EARLY"/"WATCH" verdicts — the ahead-of-the-
    crowd plays — and drops everything already priced in.
    """

    signals: list[Signal] = []
    for source in sources:
        for candidate in source.candidates():
            sig = score_candidate(
                candidate, weights, cheap_ref=cheap_ref, rich_ref=rich_ref
            )
            if sig.score < min_score:
                continue
            if only_early and sig.verdict not in EARLY_VERDICTS:
                continue
            signals.append(sig)

    signals.sort(key=lambda s: s.score, reverse=True)
    return signals
