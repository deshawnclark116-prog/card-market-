"""Google Trends as a live 'how hyped is he already' meter.

This is what turns "getting good" into "getting good but nobody's noticed yet"
— i.e. an actual sleeper. A player the crowd is already searching for (Elly De
La Cruz) has expensive cards and no edge; a player with near-zero search volume
who's quietly leveling up is the real find.

Trends returns interest normalized 0-100 *within each request*, so values from
different requests aren't comparable. We fix that by putting one **anchor**
player in every batch and expressing everyone else as a percent of the anchor —
now all players are comparable across batches in "anchor units."

Needs ``pytrends`` (imported lazily). Degrades gracefully to ``{}`` if it's not
installed or Trends rate-limits us.
"""

from __future__ import annotations

import time


def _mean_ignore_partial(df, col: str) -> float:
    sub = df
    if "isPartial" in df.columns:
        sub = df[df["isPartial"] == False]  # noqa: E712 (pandas mask)
    vals = [v for v in sub[col].tolist() if v is not None]
    return sum(vals) / len(vals) if vals else 0.0


def fetch_interest(
    names: list[str],
    *,
    anchor: str = "Aaron Judge",
    timeframe: str = "today 3-m",
    pause: float = 1.5,
) -> dict[str, float]:
    """Anchor-normalized recent search interest per name (anchor == 100 units).

    Returns {name: interest} for as many names as we could measure. Lower =
    less hype = more of a sleeper. Empty dict on failure.
    """

    try:
        from pytrends.request import TrendReq
    except ImportError:
        return {}

    targets = [n for n in names if n and n != anchor]
    if not targets:
        return {}

    try:
        py = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
    except Exception:
        return {}

    out: dict[str, float] = {}
    # 4 real names + the anchor per request (Trends caps at 5 terms).
    for i in range(0, len(targets), 4):
        batch = targets[i : i + 4]
        terms = [anchor] + batch
        try:
            py.build_payload(terms, timeframe=timeframe)
            df = py.interest_over_time()
        except Exception:
            continue
        if df is None or df.empty or anchor not in df.columns:
            continue
        anchor_mean = _mean_ignore_partial(df, anchor)
        if anchor_mean <= 0:
            continue
        for name in batch:
            if name in df.columns:
                out[name] = round(_mean_ignore_partial(df, name) / anchor_mean * 100.0, 1)
        time.sleep(pause)  # be polite; Trends rate-limits hard

    return out


# A player at/above this percent of the anchor's search volume is "already
# hyped" — cards likely priced in.
_HYPE_FULL = 40.0


def hype01(interest: float | None) -> float:
    """0-1 hype level from anchor-normalized interest (higher = more hyped)."""

    if interest is None:
        return 0.5  # unknown — treat as neutral
    return max(0.0, min(1.0, interest / _HYPE_FULL))
