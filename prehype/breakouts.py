"""Player-first breakout scan.

The right funnel: start with the small pile (players about to pop), not the
giant pile (every cheap card).

    ALL hitters --> who's about to break out? --> (top few) --> check card price
                    (Statcast leading signal)                    (eBay, only now)

Because the price check runs only on the handful that pass the breakout filter,
it's a few eBay lookups instead of thousands — which also sidesteps most of
eBay's rate/IP blocking.
"""

from __future__ import annotations

from dataclasses import dataclass

from prehype.sources.ebay import (
    EbayCompsClient,
    price_series_from_comps,
    trim_price_outliers,
)
from prehype.sources.savant import (
    SavantBatter,
    breakout_reason,
    breakout_score,
    fetch_expected_stats,
)


@dataclass
class BreakoutHit:
    """A player who cleared the breakout filter, optionally with a card price."""

    batter: SavantBatter
    score: float
    reason: str
    median_price: float | None = None  # filled only if we checked eBay
    comp_count: int = 0

    def as_alert(self) -> str:
        price = (
            f"~${self.median_price:,.0f} ({self.comp_count} comps)"
            if self.median_price is not None
            else "price not checked"
        )
        return (
            f"🔎 {self.batter.name} — breakout {self.score:.0f}/100 | cards {price}\n"
            f"   • {self.reason}"
        )


def _auto_card_query(name: str) -> str:
    """Rough eBay query for a player's key card. Refine per player later."""

    return f"{name} rookie card PSA 10"


def find_breakouts(
    *,
    year: int | None = None,
    min_pa: int = 150,
    top: int = 15,
    min_score: float = 40.0,
    batters: list[SavantBatter] | None = None,
) -> list[BreakoutHit]:
    """Scan hitters and return the top breakout candidates (no price yet).

    Pass ``batters`` to score a supplied list (used in tests); otherwise it
    fetches live from Baseball Savant.
    """

    batters = batters if batters is not None else fetch_expected_stats(year)
    hits: list[BreakoutHit] = []
    for b in batters:
        if b.pa < min_pa:
            continue
        s = breakout_score(b)
        if s < min_score:
            continue
        hits.append(BreakoutHit(batter=b, score=s, reason=breakout_reason(b)))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top]


def add_prices(
    hits: list[BreakoutHit],
    *,
    client: EbayCompsClient | None = None,
) -> list[BreakoutHit]:
    """Second stage: check eBay card prices for the breakout shortlist only."""

    client = client or EbayCompsClient()
    for h in hits:
        comps = trim_price_outliers(client.sold_comps(_auto_card_query(h.batter.name)))
        h.comp_count = len(comps)
        price = price_series_from_comps(comps)
        h.median_price = price.latest
    return hits
