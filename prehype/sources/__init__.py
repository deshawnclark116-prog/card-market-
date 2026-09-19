"""Data sources feed :class:`~prehype.models.Candidate` objects into the pipeline.

Each source knows how to build the three signal series for some universe of
players. Swap them freely — the scorer doesn't care where the numbers came
from, only that they're comparable.
"""

from prehype.sources.base import DataSource

__all__ = ["DataSource"]
