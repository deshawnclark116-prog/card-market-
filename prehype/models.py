"""Core data structures.

Everything the scorer needs about a player/card is expressed as three time
series plus some static context:

* :class:`PerformanceSeries` — the leading signal. A composite "fundamentals"
  index over time (the higher and the faster-rising, the stronger the breakout
  thesis).
* :class:`AttentionSeries` — the coincident signal. How much the crowd is
  looking (search interest, social mentions, sales *velocity*). Low = early.
* :class:`PriceSeries` — the lagging signal. What the cards actually cost. We
  want this still asleep.

A :class:`Candidate` bundles those together for one player. A :class:`Signal`
is what the scorer hands back: the number, the component breakdown, a verdict,
and plain-English reasons you can drop straight into an alert.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Sequence


@dataclass(frozen=True)
class Point:
    """A single (date, value) observation."""

    on: date
    value: float


@dataclass
class _Series:
    """A time-ordered list of observations (oldest first)."""

    points: list[Point] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.points = sorted(self.points, key=lambda p: p.on)

    @property
    def values(self) -> list[float]:
        return [p.value for p in self.points]

    @property
    def latest(self) -> float | None:
        return self.points[-1].value if self.points else None

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self.points)

    @classmethod
    def of(cls, pairs: Sequence[tuple[date, float]]):
        return cls([Point(on, v) for on, v in pairs])


class PerformanceSeries(_Series):
    """Composite fundamentals index over time (0-100, peer-normalized).

    Sources are responsible for turning raw stats into a single number where
    higher = better relative to that player's position/peers. Examples of what
    can feed it: expected stats trending up, an expanding role (snaps, plate
    appearances, minutes), age-adjusted production, prospect rank movement.
    """


class AttentionSeries(_Series):
    """Crowd-attention index over time (0-100).

    Blend of search interest, social mentions, and sales velocity. A *low*
    latest value means we are early; a rising slope from a low base is the
    first confirmation that others are starting to notice.
    """


class PriceSeries(_Series):
    """Representative card price over time (absolute dollars).

    Use one consistent reference card per player (e.g. the flagship rookie in a
    given grade) so momentum is comparable across the series.
    """


@dataclass
class Candidate:
    """A player and the three signals we track for them."""

    player_id: str
    name: str
    sport: str
    performance: PerformanceSeries
    attention: AttentionSeries
    price: PriceSeries

    # Static context that shapes risk / room-to-run.
    age: int | None = None
    role: str | None = None          # e.g. "starter", "bench", "prospect"
    injury_flag: bool = False
    reference_card: str | None = None  # what `price` actually tracks
    notes: str = ""


@dataclass
class Components:
    """The normalized 0-1 building blocks behind a score (kept for transparency)."""

    perf_level: float
    perf_momentum: float
    attn_level: float
    attn_momentum: float
    price_momentum: float
    cheapness: float
    breakout_signal: float
    opportunity: float
    risk: float


@dataclass
class Signal:
    """Scored output for one candidate."""

    candidate: Candidate
    score: float                 # 0-100 Pre-Hype Score
    verdict: str                 # short machine label, e.g. "EARLY"
    headline: str                # human one-liner for an alert
    reasons: list[str]           # bullet points explaining the score
    components: Components

    def as_alert(self) -> str:
        """Render the signal the way you'd want to read it at 7am."""

        lines = [f"{self.headline}", f"  Pre-Hype Score: {self.score:.0f}/100"]
        for r in self.reasons:
            lines.append(f"   • {r}")
        return "\n".join(lines)
