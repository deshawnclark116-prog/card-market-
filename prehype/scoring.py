"""The Pre-Hype scoring engine.

The whole system exists to answer one question per player:

    "Are this player's cards still dirt cheap and off the radar, while the
     fundamentals say a breakout is coming?"

We turn that into a number so we can rank hundreds of players automatically and
surface only the handful that are genuinely early.

Design principles
-----------------
1. **Breakout is a gate, not a bonus.** If the fundamentals aren't pointing up,
   the score collapses toward zero no matter how cheap the card is. Cheap-and-
   going-nowhere is a value trap, not an opportunity.
2. **We reward being early, not being right after the fact.** Rising price and
   rising attention *lower* the score — they mean the crowd is already arriving
   and the window is closing.
3. **Everything is transparent.** Every score ships with its component
   breakdown and plain-English reasons. No black box you can't sanity-check
   before spending money.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from prehype.models import Candidate, Components, Signal


@dataclass(frozen=True)
class ScoreWeights:
    """Tunable knobs. Defaults lean aggressively toward *early + breakout*."""

    # How the breakout thesis is built (must sum to 1.0).
    perf_level_w: float = 0.45
    perf_momentum_w: float = 0.55

    # How the "opportunity" (cheap + asleep + unnoticed) is built (sum to 1.0).
    cheapness_w: float = 0.35
    price_asleep_w: float = 0.40
    under_radar_w: float = 0.25

    # How hard risk drags the score down (0 = ignore risk, 1 = risk can zero it).
    risk_w: float = 0.5

    # Minimum breakout signal required before we bother alerting at all.
    breakout_gate: float = 0.45


def _logistic(x: float, k: float = 1.0) -> float:
    """Squash any real number into (0, 1)."""

    return 1.0 / (1.0 + math.exp(-k * x))


def _momentum(values: list[float]) -> float:
    """Rate of change of a series, mapped to 0-1 (0.5 == flat).

    Compares the recent half of the series against the earlier half. Robust to
    short series and to zero baselines.
    """

    if len(values) < 2:
        return 0.5
    mid = len(values) // 2
    earlier = values[:mid] or values[:1]
    recent = values[mid:]
    base = sum(earlier) / len(earlier)
    now = sum(recent) / len(recent)
    if base == 0:
        pct = 1.0 if now > 0 else 0.0
    else:
        pct = (now - base) / abs(base)
    # A 30% move is already a strong signal, so scale before squashing.
    return _logistic(pct, k=4.0)


def _level_0_100(value: float | None) -> float:
    """Normalize an already-0-100 index into 0-1, clamped."""

    if value is None:
        return 0.5
    return max(0.0, min(1.0, value / 100.0))


def _cheapness(price: float | None, cheap_ref: float, rich_ref: float) -> float:
    """Map absolute price to a 0-1 'room to run' score (cheaper -> higher).

    ``cheap_ref`` is the price at/below which a card is considered dirt cheap
    (score ~1); ``rich_ref`` is where it's expensive (score ~0).
    """

    if price is None:
        return 0.5
    if price <= cheap_ref:
        return 1.0
    if price >= rich_ref:
        return 0.05
    # Linear interpolation on a log scale so $5->$50 matters like $50->$500.
    lo, hi = math.log(cheap_ref), math.log(rich_ref)
    frac = (math.log(price) - lo) / (hi - lo)
    return max(0.05, 1.0 - frac)


def _risk(candidate: Candidate, price_momentum: float) -> float:
    """Aggregate downside risk into 0-1 (higher = riskier)."""

    risk = 0.0
    if candidate.injury_flag:
        risk += 0.4
    if candidate.age is not None:
        # Older players carry regression risk; young players carry bust risk.
        if candidate.age >= 32:
            risk += 0.25
        elif candidate.age <= 20:
            risk += 0.10
    # Price already running hard adds "I'm late" risk.
    if price_momentum > 0.7:
        risk += 0.25
    return min(1.0, risk)


def score_candidate(
    candidate: Candidate,
    weights: ScoreWeights | None = None,
    *,
    cheap_ref: float = 15.0,
    rich_ref: float = 500.0,
) -> Signal:
    """Compute the Pre-Hype Score and a human-readable verdict for one player.

    ``cheap_ref`` / ``rich_ref`` calibrate what "dirt cheap" vs "expensive"
    means for your reference card and grade. Tune per set/sport.
    """

    w = weights or ScoreWeights()

    perf_level = _level_0_100(candidate.performance.latest)
    perf_momentum = _momentum(candidate.performance.values)
    attn_level = _level_0_100(candidate.attention.latest)
    attn_momentum = _momentum(candidate.attention.values)
    price_momentum = _momentum(candidate.price.values)
    cheapness = _cheapness(candidate.price.latest, cheap_ref, rich_ref)

    # 1) Breakout thesis (the gate): strong, *rising* fundamentals.
    # Only genuine upward momentum counts — a flat series (momentum ~0.5)
    # contributes nothing, so cheap-but-going-nowhere never clears the gate.
    perf_uptrend = max(0.0, (perf_momentum - 0.5) * 2.0)
    breakout_signal = w.perf_level_w * perf_level + w.perf_momentum_w * perf_uptrend

    # 2) Opportunity: cheap, price asleep, crowd hasn't arrived.
    price_asleep = 1.0 - price_momentum
    under_radar = 1.0 - attn_level
    opportunity = (
        w.cheapness_w * cheapness
        + w.price_asleep_w * price_asleep
        + w.under_radar_w * under_radar
    )

    risk = _risk(candidate, price_momentum)

    # Breakout gates the whole thing; opportunity scales it; risk discounts it.
    gated = breakout_signal if breakout_signal >= w.breakout_gate else breakout_signal * 0.3
    raw = 100.0 * gated * opportunity * (1.0 - w.risk_w * risk)
    score = max(0.0, min(100.0, raw))

    verdict, headline, reasons = _explain(
        candidate,
        score,
        perf_level=perf_level,
        perf_momentum=perf_momentum,
        attn_level=attn_level,
        attn_momentum=attn_momentum,
        price_momentum=price_momentum,
        cheapness=cheapness,
        breakout_signal=breakout_signal,
        gate=w.breakout_gate,
        risk=risk,
    )

    components = Components(
        perf_level=perf_level,
        perf_momentum=perf_momentum,
        attn_level=attn_level,
        attn_momentum=attn_momentum,
        price_momentum=price_momentum,
        cheapness=cheapness,
        breakout_signal=breakout_signal,
        opportunity=opportunity,
        risk=risk,
    )

    return Signal(
        candidate=candidate,
        score=score,
        verdict=verdict,
        headline=headline,
        reasons=reasons,
        components=components,
    )


def _explain(
    candidate: Candidate,
    score: float,
    *,
    perf_level: float,
    perf_momentum: float,
    attn_level: float,
    attn_momentum: float,
    price_momentum: float,
    cheapness: float,
    breakout_signal: float,
    gate: float,
    risk: float,
) -> tuple[str, str, list[str]]:
    """Turn the numbers into a verdict, a headline, and readable reasons."""

    price = candidate.price.latest
    price_str = f"${price:,.0f}" if price is not None else "unknown price"
    reasons: list[str] = []

    strong_breakout = breakout_signal >= gate
    rising_perf = perf_momentum >= 0.6
    cheap = cheapness >= 0.6
    price_moving = price_momentum >= 0.6
    unnoticed = attn_level <= 0.4
    attention_stirring = attn_momentum >= 0.6

    # Reasons (order: thesis, then timing, then risk).
    if rising_perf:
        reasons.append("Fundamentals accelerating — breakout thesis is live")
    elif strong_breakout:
        reasons.append("Fundamentals are strong and holding")
    else:
        reasons.append("Fundamentals not pointing up yet — no breakout thesis")

    if cheap:
        reasons.append(f"Cards still dirt cheap ({price_str}) — lots of room to run")
    else:
        reasons.append(f"Cards no longer cheap ({price_str}) — upside more limited")

    if price_moving:
        reasons.append("Price already climbing — the window is closing")
    else:
        reasons.append("Price still asleep — the crowd hasn't bid it up")

    if unnoticed:
        reasons.append("Attention is low — you'd be ahead of the crowd")
    elif attention_stirring:
        reasons.append("Attention starting to stir — very first movers arriving")
    else:
        reasons.append("Already on people's radar")

    if candidate.injury_flag:
        reasons.append("⚠ Injury flag — size the position accordingly")
    if risk >= 0.5:
        reasons.append("⚠ Elevated risk (age/injury/late) baked into the score")

    # Verdict.
    if strong_breakout and cheap and not price_moving and unnoticed:
        verdict = "EARLY"
        emoji = "🔥"
        tag = "EARLY — dirt cheap, hype hasn't hit, breakout building"
    elif strong_breakout and price_moving:
        verdict = "WINDOW_CLOSING"
        emoji = "⏳"
        tag = "WINDOW CLOSING — thesis intact but price is moving"
    elif strong_breakout and not cheap:
        verdict = "TOO_LATE"
        emoji = "🚪"
        tag = "LIKELY TOO LATE — breakout real but already priced in"
    elif rising_perf or breakout_signal >= gate * 0.8:
        verdict = "WATCH"
        emoji = "👀"
        tag = "WATCH — fundamentals building, not a buy yet"
    else:
        verdict = "PASS"
        emoji = "💤"
        tag = "PASS — no breakout thesis right now"

    headline = f"{emoji} {candidate.name} ({candidate.sport}) — {tag}"
    return verdict, headline, reasons
