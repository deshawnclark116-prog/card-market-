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

from dataclasses import dataclass, field

from prehype.sources.ebay import (
    EbayCompsClient,
    price_series_from_comps,
    trim_price_outliers,
)
from prehype.sources.savant import (
    SavantBatter,
    breakout_reason,
    breakout_score,
    fetch_ages,
    fetch_expected_stats,
    fetch_pitcher_roles,
)
from prehype.sources.trends import fetch_interest, hype01

# The prospect cards worth pricing: 1st Bowman Chrome autos and rookie autos.
# These carry the real upside — not base rookies.
CARD_QUERY_BUILDERS = {
    "bowman1st": lambda name: f"{name} bowman chrome 1st auto",
    "rookieauto": lambda name: f"{name} rookie auto",
}
CARD_LABELS = {"bowman1st": "Bowman 1st auto", "rookieauto": "Rookie auto"}
DEFAULT_CARDS = ("bowman1st", "rookieauto")


@dataclass
class BreakoutHit:
    """A player who cleared the breakout filter, optionally with a card price."""

    batter: SavantBatter
    score: float
    kind: str
    reason: str
    age: int | None = None
    interest: float | None = None      # anchor-normalized search interest (hype)
    sleeper_score: float | None = None  # breakout knocked down by hype
    median_price: float | None = None  # primary card price (filled by add_prices)
    comp_count: int = 0
    # Per-card-type prices: label -> (median_price|None, comp_count)
    card_prices: dict[str, tuple[float | None, int]] = field(default_factory=dict)

    @property
    def rank_score(self) -> float:
        """What we sort by: sleeper score once hype is known, else breakout."""
        return self.sleeper_score if self.sleeper_score is not None else self.score

    @property
    def pos(self) -> str:
        """Short position tag: PIT for pitchers, BAT for hitters."""
        return "PIT" if self.batter.is_pitcher else "BAT"

    def _cards_str(self) -> str:
        if not self.card_prices:
            return "cards not checked"
        parts = []
        for label, (median, count) in self.card_prices.items():
            if median is not None:
                parts.append(f"{label} ~${median:,.0f} ({count})")
            else:
                parts.append(f"{label} n/a")
        return " | ".join(parts)

    def as_alert(self) -> str:
        if self.sleeper_score is not None:
            hype = (
                f"{self.interest:.0f}% of a star's searches"
                if self.interest is not None
                else "hype unknown"
            )
            head = (
                f"🔎 {self.batter.name} ({self.pos}) — SLEEPER {self.sleeper_score:.0f}/100 "
                f"(breakout {self.score:.0f}, hype {hype}) [{self.kind}]"
            )
        else:
            head = (
                f"🔎 {self.batter.name} ({self.pos}) — breakout {self.score:.0f}/100 "
                f"[{self.kind}]"
            )
        return f"{head}\n   • {self.reason}\n   • cards: {self._cards_str()}"


def find_breakouts(
    *,
    year: int | None = None,
    min_pa: int = 150,
    top: int = 15,
    min_score: float = 20.0,
    player_type: str = "batter",
    starters_only: bool = False,
    batters: list[SavantBatter] | None = None,
    prior: list[SavantBatter] | None = None,
    ages: dict[str, int] | None = None,
    roles: dict[str, bool] | None = None,
) -> list[BreakoutHit]:
    """Scan one player type and return the top breakout candidates (no price yet).

    Scores IMPROVEMENT (this year vs last) + youth, so sleepers rise and famous
    stars sink. ``player_type`` is "batter" or "pitcher"; ``starters_only``
    drops relievers (pitchers only). Pass ``batters``/``prior``/``ages``/``roles``
    to score supplied data (tests); otherwise fetches live.
    """

    from datetime import date as _date

    year = year or _date.today().year
    if batters is None:
        batters = fetch_expected_stats(year, kind=player_type)
        prior = fetch_expected_stats(year - 1, kind=player_type)
        ages = fetch_ages(year)
        if player_type == "pitcher" and starters_only:
            roles = fetch_pitcher_roles(year)
    prior_map = {b.player_id: b for b in (prior or [])}
    ages = ages or {}
    roles = roles or {}

    hits: list[BreakoutHit] = []
    for b in batters:
        if b.pa < min_pa:
            continue
        # Drop relievers when asked; if roles are unknown for a pitcher, keep him.
        if player_type == "pitcher" and starters_only and roles.get(b.player_id) is False:
            continue
        age = ages.get(b.player_id)
        score, kind = breakout_score(b, prior_map.get(b.player_id), age)
        if score < min_score:
            continue
        hits.append(
            BreakoutHit(
                batter=b,
                score=score,
                kind=kind,
                age=age,
                reason=breakout_reason(b, prior_map.get(b.player_id), age),
            )
        )

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top]


def find_breakouts_multi(
    *,
    year: int | None = None,
    min_pa_batter: int = 250,
    min_pa_pitcher: int = 300,
    top: int = 15,
    min_score: float = 20.0,
    types: tuple[str, ...] = ("batter", "pitcher"),
    starters_only: bool = True,
) -> list[BreakoutHit]:
    """Scan hitters and pitchers, merge, and return the top candidates overall.

    Pitchers get a higher batters-faced floor (noisy small samples) and, by
    default, are limited to starters (relievers' cards carry little value).
    """

    combined: list[BreakoutHit] = []
    for t in types:
        min_pa = min_pa_pitcher if t == "pitcher" else min_pa_batter
        combined.extend(
            find_breakouts(
                year=year,
                min_pa=min_pa,
                starters_only=starters_only,
                top=top * 3,
                min_score=min_score,
                player_type=t,
            )
        )
    combined.sort(key=lambda h: h.score, reverse=True)
    return combined[: top * 3]


def add_hype(
    hits: list[BreakoutHit],
    *,
    anchor: str = "Aaron Judge",
    interest: dict[str, float] | None = None,
) -> list[BreakoutHit]:
    """Fetch search interest for the shortlist and compute a sleeper score.

    sleeper_score = breakout score knocked down by how hyped the player already
    is. A famous name (high search volume) gets crushed; an unknown keeps almost
    all of his breakout score. Re-sorts the list by sleeper score.

    Pass ``interest`` to supply values (tests); otherwise fetches live.
    """

    names = [h.batter.name for h in hits]
    interest = interest if interest is not None else fetch_interest(names, anchor=anchor)

    for h in hits:
        val = interest.get(h.batter.name)
        h.interest = val
        h.sleeper_score = round(h.score * (1.0 - hype01(val)), 1)

    hits.sort(key=lambda h: h.rank_score, reverse=True)
    return hits


def add_prices(
    hits: list[BreakoutHit],
    *,
    client: EbayCompsClient | None = None,
    cards: tuple[str, ...] = DEFAULT_CARDS,
) -> list[BreakoutHit]:
    """Second stage: check eBay card prices for the breakout shortlist only.

    Prices the prospect cards that actually carry upside — Bowman Chrome 1st
    autos and rookie autos by default. Runs only on the shortlist, so it's a
    handful of eBay lookups.
    """

    client = client or EbayCompsClient()
    for h in hits:
        h.card_prices = {}
        for card in cards:
            label = CARD_LABELS.get(card, card)
            query = CARD_QUERY_BUILDERS[card](h.batter.name)
            comps = trim_price_outliers(client.sold_comps(query))
            median = price_series_from_comps(comps).latest
            h.card_prices[label] = (median, len(comps))
        # Primary = first configured card type that returned a price.
        for card in cards:
            median, count = h.card_prices[CARD_LABELS.get(card, card)]
            if median is not None:
                h.median_price = median
                h.comp_count = count
                break
    return hits
