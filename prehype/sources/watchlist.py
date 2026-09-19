"""Watchlist source: score real cards you care about, priced by eBay comps.

You give it a small JSON file of players + the exact eBay search that isolates
their reference card. It pulls real sold comps and builds:

* **price** from the weekly median sold price (real price momentum + cheapness)
* **attention** from weekly sales velocity (the early crowd signal)

Performance (the breakout gate) comes from whatever you can give it:

* ``"performance": [40, 48, 56, 65, 74, 82]`` — a hand-entered fundamentals read
  (weekly, oldest first), or
* nothing yet — then it's treated as flat and the card won't clear the breakout
  gate until you wire a real performance feed for that sport.

Watchlist file format (see ``watchlist.example.json``)::

    {
      "defaults": {"cheap_ref": 15, "rich_ref": 500},
      "players": [
        {
          "player_id": "julio-rodriguez",
          "name": "Julio Rodriguez",
          "sport": "MLB",
          "ebay_query": "2022 Topps Chrome Julio Rodriguez RC PSA 10",
          "performance": [55, 60, 66, 72, 79, 85],
          "age": 24,
          "role": "starter"
        }
      ]
    }
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, timedelta

from prehype.models import (
    AttentionSeries,
    Candidate,
    PerformanceSeries,
)
from prehype.sources.base import DataSource
from prehype.sources.ebay import (
    EbayCompsClient,
    price_series_from_comps,
    trim_price_outliers,
    velocity_series_from_comps,
)


def _weekly(values: list[float]) -> list[tuple[date, float]]:
    start = date.today() - timedelta(weeks=len(values) - 1)
    return [(start + timedelta(weeks=i), float(v)) for i, v in enumerate(values)]


class WatchlistSource(DataSource):
    """Build candidates from a watchlist file, priced by real eBay comps."""

    name = "ebay"

    def __init__(
        self,
        path: str,
        *,
        client: EbayCompsClient | None = None,
        weeks: int = 8,
    ) -> None:
        self.path = path
        self.client = client or EbayCompsClient()
        self.weeks = weeks

    def candidates(self) -> Iterable[Candidate]:
        with open(self.path, encoding="utf-8") as f:
            spec = json.load(f)

        for entry in spec.get("players", []):
            query = entry.get("ebay_query")
            if not query:
                continue
            comps = trim_price_outliers(self.client.sold_comps(query, max_results=240))

            price = price_series_from_comps(comps, weeks=self.weeks)
            attention = velocity_series_from_comps(comps, weeks=self.weeks)

            perf_values = entry.get("performance")
            performance = (
                PerformanceSeries.of(_weekly(perf_values))
                if perf_values
                else PerformanceSeries.of([])
            )
            # If eBay gave us nothing (e.g. blocked IP, no comps), we still emit
            # the candidate with empty series so you can see it was checked.
            if not attention.points and perf_values is None:
                attention = AttentionSeries.of([])

            yield Candidate(
                player_id=entry.get("player_id", query),
                name=entry.get("name", query),
                sport=entry.get("sport", "?"),
                performance=performance,
                attention=attention,
                price=price,
                age=entry.get("age"),
                role=entry.get("role"),
                injury_flag=bool(entry.get("injury_flag", False)),
                reference_card=query,
                notes=f"{len(comps)} eBay sold comps",
            )
