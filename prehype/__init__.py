"""prehype — detect sports cards *before* the market prices in the hype.

The thesis in one line: price is the last thing to move. Performance and
attention move first. We buy the gap.

    on-field performance / news  ->  attention (search, social, sales velocity)  ->  price
            (leading)                        (coincident)                            (lagging)

The :mod:`prehype.scoring` module turns that chain into a single, transparent
Pre-Hype Score so we can rank candidates by how wide their opportunity window
still is.
"""

from prehype.models import (
    AttentionSeries,
    PerformanceSeries,
    PriceSeries,
    Candidate,
    Signal,
)
from prehype.scoring import ScoreWeights, score_candidate

__all__ = [
    "AttentionSeries",
    "PerformanceSeries",
    "PriceSeries",
    "Candidate",
    "Signal",
    "ScoreWeights",
    "score_candidate",
]

__version__ = "0.1.0"
