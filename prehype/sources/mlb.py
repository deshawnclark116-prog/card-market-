"""A real, free performance feed: the MLB Stats API (statsapi.mlb.com).

No API key required. This shows the shape of a *real* source: pull raw stats,
turn them into a rolling composite fundamentals index, and hand back candidates.

It only fills the ``performance`` series from live data. Attention and price
still need real feeds (eBay sold comps, Google Trends, sales velocity) — those
are the paid/scraped parts of the moat and are left as clearly marked stubs so
you can see exactly where they plug in.

Network access is best-effort: if the API can't be reached, the source yields
nothing rather than crashing the pipeline, so ``demo`` still works offline.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterable
from datetime import date, timedelta

from prehype.models import (
    AttentionSeries,
    Candidate,
    PerformanceSeries,
    PriceSeries,
)
from prehype.sources.base import DataSource

_STATS_URL = (
    "https://statsapi.mlb.com/api/v1/stats"
    "?stats=byDateRange&group=hitting&gameType=R&sportId=1"
    "&startDate={start}&endDate={end}&limit={limit}"
)


def _fetch(url: str, timeout: float = 10.0) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "prehype/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def _ops_to_index(ops: float) -> float:
    """Map OPS onto a rough 0-100 fundamentals index.

    .600 OPS -> ~20, .800 -> ~60, 1.000 -> ~100. A stand-in until you feed it a
    proper age/role/expected-stats composite.
    """

    idx = (ops - 0.500) / 0.500 * 100.0
    return max(0.0, min(100.0, idx))


class MLBStatsSource(DataSource):
    """Live hitter fundamentals from the MLB Stats API.

    Builds a multi-week performance series by querying several trailing date
    windows, so the scorer can read momentum, not just a single snapshot.
    """

    name = "mlb"

    def __init__(self, weeks: int = 6, players: int = 40) -> None:
        self.weeks = weeks
        self.players = players

    def candidates(self) -> Iterable[Candidate]:
        # player_id -> {name, [(week_end_date, index), ...]}
        series: dict[int, dict] = {}
        today = date.today()

        for w in range(self.weeks, 0, -1):
            end = today - timedelta(weeks=w - 1)
            start = end - timedelta(days=6)
            data = _fetch(
                _STATS_URL.format(start=start, end=end, limit=self.players)
            )
            if not data:
                continue
            splits = (data.get("stats") or [{}])[0].get("splits", [])
            for split in splits:
                player = split.get("player", {})
                pid = player.get("id")
                stat = split.get("stat", {})
                ops = stat.get("ops")
                if pid is None or ops is None:
                    continue
                try:
                    ops_f = float(ops)
                except (TypeError, ValueError):
                    continue
                rec = series.setdefault(pid, {"name": player.get("fullName", str(pid)), "pts": []})
                rec["pts"].append((end, _ops_to_index(ops_f)))

        for pid, rec in series.items():
            pts = rec["pts"]
            if len(pts) < 2:
                continue  # need at least two points to read momentum
            yield Candidate(
                player_id=f"mlb-{pid}",
                name=rec["name"],
                sport="MLB",
                performance=PerformanceSeries.of(pts),
                # TODO: wire real attention (Google Trends / sales velocity).
                attention=AttentionSeries.of([(d, 25.0) for d, _ in pts]),
                # TODO: wire real price (eBay sold comps / Card Ladder).
                price=PriceSeries.of([(d, 20.0) for d, _ in pts]),
                role="mlb",
                notes="Performance from MLB StatsAPI; attention/price are stubs.",
            )
