"""Minor-league prospect scanner — find the next name before it's a name.

Bowman 1st autos are *prospect* cards, so the real edge lives in the minors, not
the majors. But the minors have no Statcast (xwOBA), so the leading signal is
different — and, honestly, better for prospects:

* **Age relative to level** — the single best prospect tell. A 20-year-old
  holding his own in Double-A is a screaming buy; a 25-year-old doing the same
  in A-ball is org filler. Younger-than-your-league = future star.
* **Performance** (OPS) relative to the level.
* **Plate discipline** (walk vs strikeout rate) — skill that travels up levels.
* **Level** — the same numbers mean more the closer to the majors he is.

Data comes from the MLB StatsAPI minor-league feeds (free). Same downstream
funnel afterward: low hype + Bowman 1st auto still cheap + price not already
moving.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

_UA = "Mozilla/5.0 (prehype/0.1)"

# sportId -> (label, typical age at level, how much to trust it toward payoff)
LEVELS: dict[int, tuple[str, float, float]] = {
    11: ("AAA", 25.0, 1.00),
    12: ("AA", 23.5, 0.95),
    13: ("A+", 22.0, 0.85),
    14: ("A", 20.8, 0.72),
}

_HIT_URL = (
    "https://statsapi.mlb.com/api/v1/stats?stats=season&group=hitting"
    "&season={year}&sportId={sid}&gameType=R&playerPool=ALL&limit=2000"
)
_PLAYERS_URL = "https://statsapi.mlb.com/api/v1/sports/{sid}/players?season={year}"


@dataclass
class MilbBatter:
    """A minor-league hitter's line (enough to judge a prospect)."""

    player_id: str
    name: str
    level: str
    age: int | None
    pa: int
    ops: float
    bb_rate: float
    k_rate: float
    hr: int
    is_pitcher: bool = False  # so it plugs into the same BreakoutHit/serializer


def _to_float(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fetch(url: str, timeout: float = 25.0) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def _fetch_ages(sid: int, year: int) -> dict[str, int]:
    data = _fetch(_PLAYERS_URL.format(sid=sid, year=year))
    ages: dict[str, int] = {}
    if not data:
        return ages
    for p in data.get("people", []):
        pid, age = p.get("id"), p.get("currentAge")
        if pid is not None and age is not None:
            ages[str(pid)] = int(age)
    return ages


def fetch_level(year: int, sid: int) -> list[MilbBatter]:
    """Fetch one minor-league level's hitters. [] on failure."""

    label = LEVELS.get(sid, (str(sid), 22.0, 0.7))[0]
    data = _fetch(_HIT_URL.format(year=year, sid=sid))
    if not data:
        return []
    ages = _fetch_ages(sid, year)
    out: list[MilbBatter] = []
    for split in (data.get("stats") or [{}])[0].get("splits", []):
        player = split.get("player", {})
        pid = player.get("id")
        stat = split.get("stat", {})
        pa = int(_to_float(stat.get("plateAppearances")) or 0)
        ops = _to_float(stat.get("ops"))
        if pid is None or ops is None or pa <= 0:
            continue
        bb = _to_float(stat.get("baseOnBalls")) or 0.0
        k = _to_float(stat.get("strikeOuts")) or 0.0
        out.append(
            MilbBatter(
                player_id=str(pid),
                name=player.get("fullName", str(pid)),
                level=label,
                age=ages.get(str(pid)),
                pa=pa,
                ops=ops,
                bb_rate=bb / pa if pa else 0.0,
                k_rate=k / pa if pa else 0.0,
                hr=int(_to_float(stat.get("homeRuns")) or 0),
            )
        )
    return out


# --------------------------------------------------------------------------- #
# Prospect score (age-for-level is the star of the show).
# --------------------------------------------------------------------------- #

_OPS_FLOOR, _OPS_ELITE = 0.700, 0.950


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def prospect_score(b: MilbBatter) -> tuple[float, str]:
    """0-100 prospect breakout score + kind ("prospect")."""

    _, level_age, level_weight = next(
        (v for v in LEVELS.values() if v[0] == b.level), (b.level, 22.0, 0.7)
    )

    perf01 = _clamp01((b.ops - _OPS_FLOOR) / (_OPS_ELITE - _OPS_FLOOR))

    # Age relative to level: younger than the level's typical age = elite.
    if b.age is None:
        youth01 = 0.5
    else:
        youth01 = _clamp01((level_age - b.age) / 3.0)  # 3+ yrs young = full

    # Plate discipline travels up levels: reward walks and low strikeouts.
    # A high walk rate in a young hitter is one of the best breakout tells.
    bb01 = _clamp01((b.bb_rate - 0.06) / (0.15 - 0.06))       # 6% floor, 15% elite
    lowk01 = _clamp01((0.25 - b.k_rate) / (0.25 - 0.12))      # <=12% K = full
    disc01 = 0.5 * bb01 + 0.5 * lowk01

    base = perf01 * (0.35 + 0.65 * youth01) * (0.75 + 0.25 * disc01)
    return round(min(1.0, base) * 100.0 * level_weight, 1), "prospect"


def prospect_reason(b: MilbBatter) -> str:
    _, level_age, _ = next(
        (v for v in LEVELS.values() if v[0] == b.level), (b.level, 22.0, 0.7)
    )
    age_note = ""
    if b.age is not None:
        if b.age <= level_age - 1.5:
            age_note = f"age {b.age} in {b.level} (young for the level) — "
        else:
            age_note = f"age {b.age} in {b.level} — "
    return (
        f"{age_note}{b.ops:.3f} OPS, {b.bb_rate:.0%} BB, {b.k_rate:.0%} K"
        f"{f', {b.hr} HR' if b.hr else ''}"
    )
