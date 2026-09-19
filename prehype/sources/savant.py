"""Baseball Savant (Statcast) — the *leading* breakout signal.

The old MLB feed used surface stats (OPS): by the time those look hot, the
market already knows, so you're not early. Statcast fixes that by measuring how
well a hitter is *actually* striking the ball, which shows up before the results
— and before the crowd — catch on.

Two numbers do the heavy lifting:

* **Expected wOBA (``est_woba``)** — quality of contact. High = genuinely elite
  skill, regardless of results so far.
* **The luck gap (actual wOBA − expected wOBA)** — when it's *negative*, the
  player is hitting the ball better than his stat line shows. He's "unlucky,"
  his numbers are a coiled spring about to jump, and because casual fans watch
  the box score his cards are still cheap. That is precisely "ahead of the
  crowd."

So a breakout candidate = **elite quality of contact + results still lagging.**
This module fetches the leaderboard and turns it into a 0-100 breakout score,
player-first, before we ever look at a price.
"""

from __future__ import annotations

import csv
import io
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date

_CSV_URL = (
    "https://baseballsavant.mlb.com/leaderboard/expected_statistics"
    "?type=batter&year={year}&position=&team=&filterType=bip&min={min_bip}&csv=true"
)
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


@dataclass
class SavantBatter:
    """One hitter's Statcast expected-stats line."""

    player_id: str
    name: str            # "First Last"
    year: int
    pa: int
    woba: float          # actual wOBA (what the box score reflects)
    est_woba: float      # expected wOBA (quality of contact)
    est_slg: float       # expected slugging (power under the hood)

    @property
    def luck_gap(self) -> float:
        """actual − expected. Negative = unlucky = results due to rise."""
        return round(self.woba - self.est_woba, 4)


def _to_float(s: str) -> float | None:
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_expected_stats(csv_text: str, year: int) -> list[SavantBatter]:
    """Parse a Savant expected-statistics CSV into batters (resilient)."""

    # Strip a leading BOM if present so the first header key matches.
    csv_text = csv_text.lstrip("﻿")
    reader = csv.DictReader(io.StringIO(csv_text))
    out: list[SavantBatter] = []
    for row in reader:
        name_field = (row.get("last_name, first_name") or "").strip()
        if not name_field:
            continue
        # "Duran, Jarren" -> "Jarren Duran"
        if ", " in name_field:
            last, first = name_field.split(", ", 1)
            name = f"{first} {last}"
        else:
            name = name_field
        est_woba = _to_float(row.get("est_woba"))
        woba = _to_float(row.get("woba"))
        if est_woba is None or woba is None:
            continue
        out.append(
            SavantBatter(
                player_id=(row.get("player_id") or "").strip(),
                name=name,
                year=year,
                pa=int(_to_float(row.get("pa")) or 0),
                woba=woba,
                est_woba=est_woba,
                est_slg=_to_float(row.get("est_slg")) or 0.0,
            )
        )
    return out


def fetch_expected_stats(
    year: int | None = None, *, min_bip: int = 50, timeout: float = 25.0
) -> list[SavantBatter]:
    """Download the batter expected-stats leaderboard. Returns [] on failure."""

    year = year or date.today().year
    url = _CSV_URL.format(year=year, min_bip=min_bip)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "text/csv,*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, ValueError):
        return []
    return parse_expected_stats(text, year)


# --------------------------------------------------------------------------- #
# The breakout score (player-first, no price involved yet).
# --------------------------------------------------------------------------- #

# Calibration anchors for wOBA/xSLG. League-average wOBA sits ~.310-.320; .400+
# is elite. xSLG ~.400 average, .600 elite.
_WOBA_FLOOR, _WOBA_ELITE = 0.300, 0.420
_SLG_FLOOR, _SLG_ELITE = 0.380, 0.600
_LUCK_FULL = 0.030  # a .030 unlucky gap is a big coiled spring


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def breakout_score(b: SavantBatter) -> float:
    """0-100: elite quality of contact, amplified when results still lag it."""

    woba_skill = _clamp01((b.est_woba - _WOBA_FLOOR) / (_WOBA_ELITE - _WOBA_FLOOR))
    power_skill = _clamp01((b.est_slg - _SLG_FLOOR) / (_SLG_ELITE - _SLG_FLOOR))
    skill = 0.7 * woba_skill + 0.3 * power_skill

    # Unlucky (actual < expected) is the leading edge; cap the bonus.
    underrated = _clamp01((-b.luck_gap) / _LUCK_FULL)

    # Skill gates the score; being unlucky amplifies it.
    return round(100.0 * skill * (0.55 + 0.45 * underrated), 1)


def breakout_reason(b: SavantBatter) -> str:
    """A one-line, plain-English 'why' for an alert."""

    gap = b.luck_gap
    if gap <= -0.020:
        luck = f"crushing the ball but unlucky (stats {abs(gap):.3f} below his contact) — due to jump"
    elif gap < 0:
        luck = "hitting better than his line shows — trending up"
    elif gap <= 0.010:
        luck = "results roughly match his contact quality"
    else:
        luck = f"slightly overperforming (careful — some luck baked in)"
    return f"xwOBA {b.est_woba:.3f} (elite ~.400); {luck}"
