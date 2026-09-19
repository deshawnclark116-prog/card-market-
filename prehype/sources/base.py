"""The data-source contract.

Implement :meth:`DataSource.candidates` to plug a new feed into the pipeline.
Where the numbers come from is up to you; the pipeline and scorer only depend
on this interface.

Real sources you'd add over time (all of these are the actual moat):

* **Performance:** MLB StatsAPI (free, no key), NBA/NFL stats endpoints,
  minor-league / prospect boards, expected-stats providers.
* **Attention:** Google Trends (pytrends), Reddit/X mention counts, and — the
  best one — *sales velocity* (how many comps sold this week vs last).
* **Price:** eBay sold comps, 130point, Card Ladder-style series, auction
  results.
"""

from __future__ import annotations

import abc
from collections.abc import Iterable

from prehype.models import Candidate


class DataSource(abc.ABC):
    """A provider of scored-ready candidates."""

    name: str = "unnamed"

    @abc.abstractmethod
    def candidates(self) -> Iterable[Candidate]:
        """Yield candidates with performance / attention / price series filled in."""
        raise NotImplementedError
