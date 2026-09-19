"""A synthetic data source so the whole system runs end-to-end offline.

These are made-up players chosen to exercise every verdict the scorer can
produce, so ``python -m prehype scan`` shows something meaningful before you've
wired up a single real API. Replace with real sources when ready — nothing else
in the pipeline changes.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

from prehype.models import (
    AttentionSeries,
    Candidate,
    PerformanceSeries,
    PriceSeries,
)
from prehype.sources.base import DataSource


def _weekly(values: list[float]) -> list[tuple[date, float]]:
    """Attach weekly dates (oldest first) to a list of values."""

    start = date.today() - timedelta(weeks=len(values) - 1)
    return [(start + timedelta(weeks=i), v) for i, v in enumerate(values)]


class DemoSource(DataSource):
    """Hand-crafted candidates spanning the full range of outcomes."""

    name = "demo"

    def candidates(self) -> Iterable[Candidate]:
        yield Candidate(
            player_id="demo-1",
            name="Jalen Rooke",
            sport="MLB",
            # Fundamentals ramping hard; a real breakout forming.
            performance=PerformanceSeries.of(_weekly([40, 44, 51, 58, 66, 75])),
            # Barely anyone watching yet.
            attention=AttentionSeries.of(_weekly([12, 13, 12, 15, 17, 20])),
            # Price flat and cheap — the sweet spot.
            price=PriceSeries.of(_weekly([8, 8, 9, 8, 9, 10])),
            age=22,
            role="prospect",
            reference_card="2024 flagship RC, PSA 10",
            notes="Called up recently, expanding role.",
        )
        yield Candidate(
            player_id="demo-2",
            name="Marcus Vane",
            sport="NBA",
            # Strong and rising fundamentals...
            performance=PerformanceSeries.of(_weekly([55, 60, 66, 71, 78, 84])),
            # ...but the crowd is already piling in and price is moving.
            attention=AttentionSeries.of(_weekly([30, 38, 50, 62, 74, 85])),
            price=PriceSeries.of(_weekly([25, 30, 42, 60, 90, 130])),
            age=24,
            role="starter",
            reference_card="2023 Prizm RC, PSA 10",
            notes="Already trending — likely too late.",
        )
        yield Candidate(
            player_id="demo-3",
            name="Diego Salas",
            sport="MLB",
            # Fundamentals flat — value trap.
            performance=PerformanceSeries.of(_weekly([48, 47, 49, 46, 48, 47])),
            attention=AttentionSeries.of(_weekly([15, 14, 16, 15, 14, 15])),
            price=PriceSeries.of(_weekly([6, 6, 7, 6, 6, 6])),
            age=27,
            role="bench",
            reference_card="2022 flagship RC, PSA 10",
            notes="Cheap, but going nowhere.",
        )
        yield Candidate(
            player_id="demo-4",
            name="Theo Bricks",
            sport="NFL",
            # Building, not yet a buy.
            performance=PerformanceSeries.of(_weekly([42, 45, 48, 52, 55, 58])),
            attention=AttentionSeries.of(_weekly([18, 20, 22, 25, 24, 27])),
            price=PriceSeries.of(_weekly([11, 12, 12, 13, 12, 13])),
            age=23,
            role="starter",
            reference_card="2023 Prizm RC, PSA 10",
            notes="On the cusp — watch.",
        )
        yield Candidate(
            player_id="demo-5",
            name="Ken Ishida",
            sport="MLB",
            # Great thesis, cheap, quiet — but hurt.
            performance=PerformanceSeries.of(_weekly([50, 55, 62, 70, 77, 83])),
            attention=AttentionSeries.of(_weekly([14, 15, 16, 18, 19, 22])),
            price=PriceSeries.of(_weekly([12, 12, 13, 12, 13, 14])),
            age=21,
            role="prospect",
            injury_flag=True,
            reference_card="2024 flagship RC, PSA 10",
            notes="Breakout profile but currently on the IL.",
        )
