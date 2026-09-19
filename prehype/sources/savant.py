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
    "?type={kind}&year={year}&position=&team=&filterType=bip&min={min_bip}&csv=true"
)
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


@dataclass
class SavantBatter:
    """One player's Statcast expected-stats line (a hitter or a pitcher).

    For a pitcher these are the numbers *allowed*: ``est_woba`` is xwOBA-against,
    where **lower is better** (harder to hit). ``player_type`` says which.
    """

    player_id: str
    name: str            # "First Last"
    year: int
    pa: int
    woba: float          # actual wOBA (or wOBA allowed, for a pitcher)
    est_woba: float      # expected wOBA (quality of contact, or contact allowed)
    est_slg: float       # expected slugging (allowed, for a pitcher)
    player_type: str = "batter"  # "batter" or "pitcher"

    @property
    def is_pitcher(self) -> bool:
        return self.player_type == "pitcher"

    @property
    def luck_gap(self) -> float:
        """actual − expected. For a hitter, negative = unlucky = results due to rise."""
        return round(self.woba - self.est_woba, 4)


def _to_float(s: str) -> float | None:
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_expected_stats(
    csv_text: str, year: int, *, kind: str = "batter"
) -> list[SavantBatter]:
    """Parse a Savant expected-statistics CSV into players (resilient)."""

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
                player_type=kind,
            )
        )
    return out


def fetch_expected_stats(
    year: int | None = None, *, kind: str = "batter", min_bip: int = 50, timeout: float = 25.0
) -> list[SavantBatter]:
    """Download the expected-stats leaderboard (batter or pitcher). [] on failure."""

    year = year or date.today().year
    url = _CSV_URL.format(kind=kind, year=year, min_bip=min_bip)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "text/csv,*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, ValueError):
        return []
    return parse_expected_stats(text, year, kind=kind)


# --------------------------------------------------------------------------- #
# Player ages (one call, so we can favor young players).
# --------------------------------------------------------------------------- #

_PLAYERS_URL = "https://statsapi.mlb.com/api/v1/sports/1/players?season={year}"


def fetch_ages(year: int | None = None, *, timeout: float = 25.0) -> dict[str, int]:
    """player_id -> current age, in one MLB StatsAPI call. {} on failure."""

    year = year or date.today().year
    try:
        req = urllib.request.Request(
            _PLAYERS_URL.format(year=year), headers={"User-Agent": _UA, "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            import json

            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return {}
    ages: dict[str, int] = {}
    for p in data.get("people", []):
        pid, age = p.get("id"), p.get("currentAge")
        if pid is not None and age is not None:
            ages[str(pid)] = int(age)
    return ages


# --------------------------------------------------------------------------- #
# The breakout score — IMPROVEMENT, not level.
# --------------------------------------------------------------------------- #
#
# Ranking by skill level just lists the stars (already famous, cards expensive,
# no edge). A real sleeper is someone who was average/unknown and quietly
# *leveled up*, or a young new face emerging. So we score:
#
#   * the JUMP in quality of contact vs last year (big positive = leveling up),
#   * gated so it only counts if they weren't already a star last year,
#   * a youth boost (young cards have the most upside),
#   * rookies/new faces with strong contact as "emerging".
#
# Established stars score low here: their year-over-year jump is ~zero and their
# prior level was already elite, so the "was under the radar" gate zeroes them.

# Hitters: higher xwOBA is better.
_LEAGUE_WOBA = 0.315
_JUMP_FULL = 0.045       # a +.045 xwOBA jump year-over-year is huge
_STAR_PRIOR = 0.360      # prior xwOBA at/above this = already known
_PRIOR_MIN_PA = 150      # need a real prior sample to call it a "jump"

# Pitchers: it's xwOBA-*against*, so LOWER is better and a "jump" is a DROP.
_PITCH_LEAGUE = 0.320    # ~league-average contact allowed
_PITCH_ELITE = 0.260     # elite (very hard to hit)
_PITCH_STAR = 0.300      # prior at/below this = already an elite arm (not hidden)
_PITCH_HITTABLE = 0.360  # prior this high = was very hittable (lots of room)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _youth_mult(age: int | None) -> float:
    """Multiplier: young players boosted, older ones discounted."""

    if age is None:
        return 1.0
    youth01 = _clamp01((27 - age) / (27 - 21))  # <=21 full, >=27 none
    return 0.7 + 0.5 * youth01                   # 0.7x (old) .. 1.2x (very young)


def _batter_breakout(cur: SavantBatter, prior: "SavantBatter | None") -> tuple[float, str]:
    now = cur.est_woba
    if prior is None or prior.pa < _PRIOR_MIN_PA:
        base = _clamp01((now - _LEAGUE_WOBA) / (0.420 - _LEAGUE_WOBA))
        return base * 0.85, "emerging"
    jump = now - prior.est_woba
    jump01 = _clamp01(jump / _JUMP_FULL)
    under_radar01 = _clamp01((_STAR_PRIOR - prior.est_woba) / (_STAR_PRIOR - 0.290))
    now_ok01 = _clamp01((now - 0.310) / (0.375 - 0.310))
    return jump01 * (0.35 + 0.65 * under_radar01) * (0.40 + 0.60 * now_ok01), "leveling up"


def _pitcher_breakout(cur: SavantBatter, prior: "SavantBatter | None") -> tuple[float, str]:
    # Lower xwOBA-against is better; improvement is a DROP.
    now = cur.est_woba
    if prior is None or prior.pa < _PRIOR_MIN_PA:
        base = _clamp01((_PITCH_LEAGUE - now) / (_PITCH_LEAGUE - _PITCH_ELITE))
        return base * 0.85, "emerging"
    drop = prior.est_woba - now                       # positive = harder to hit now
    drop01 = _clamp01(drop / _JUMP_FULL)
    # Was he hittable last year (room to improve, not already elite)?
    under_radar01 = _clamp01((prior.est_woba - _PITCH_STAR) / (_PITCH_HITTABLE - _PITCH_STAR))
    # Is he actually nasty now (not just less bad)?
    now_ok01 = _clamp01((_PITCH_LEAGUE - now) / (_PITCH_LEAGUE - _PITCH_ELITE))
    return drop01 * (0.35 + 0.65 * under_radar01) * (0.40 + 0.60 * now_ok01), "leveling up"


def breakout_score(
    cur: SavantBatter,
    prior: "SavantBatter | None" = None,
    age: int | None = None,
) -> tuple[float, str]:
    """Return (0-100 breakout score, kind) for a hitter or pitcher.

    ``kind`` is "leveling up" (improved vs last year) or "emerging" (new face,
    no real prior-year sample).
    """

    if cur.is_pitcher:
        raw, kind = _pitcher_breakout(cur, prior)
    else:
        raw, kind = _batter_breakout(cur, prior)

    raw *= _youth_mult(age)
    return round(min(1.0, raw) * 100.0, 1), kind


def breakout_reason(
    cur: SavantBatter,
    prior: "SavantBatter | None" = None,
    age: int | None = None,
) -> str:
    """A one-line, plain-English 'why' for an alert."""

    age_str = f"age {age}, " if age is not None else ""

    if cur.is_pitcher:
        if prior is None or prior.pa < _PRIOR_MIN_PA:
            return (
                f"{age_str}new arm — already tough to hit "
                f"(xwOBA-against {cur.est_woba:.3f}, lower is better)"
            )
        drop = prior.est_woba - cur.est_woba
        direction = "dropped" if drop >= 0 else "rose"
        return (
            f"{age_str}xwOBA-against {direction} {prior.est_woba:.3f} -> {cur.est_woba:.3f} "
            f"({-drop:+.3f}) vs last year — got nastier while still under the radar"
        )

    if prior is None or prior.pa < _PRIOR_MIN_PA:
        return (
            f"{age_str}new face — strong contact already (xwOBA {cur.est_woba:.3f}, "
            f"league avg ~.315)"
        )
    jump = cur.est_woba - prior.est_woba
    direction = "jumped" if jump >= 0 else "slipped"
    return (
        f"{age_str}xwOBA {direction} {prior.est_woba:.3f} -> {cur.est_woba:.3f} "
        f"({jump:+.3f}) vs last year — leveled up while still under the radar"
    )
