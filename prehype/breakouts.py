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
    price_momentum_from_comps,
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
    price_trend: float | None = None    # primary card price change, e.g. 0.30 = +30%
    deal_score: float | None = None     # sleeper score gated by price momentum

    @property
    def rank_score(self) -> float:
        """What we sort by, best signal available: deal > sleeper > breakout."""
        if self.deal_score is not None:
            return self.deal_score
        if self.sleeper_score is not None:
            return self.sleeper_score
        return self.score

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

    def _trend_str(self) -> str:
        if self.price_trend is None:
            return "card price trend: unknown (too few sales)"
        if self.price_trend <= 0.05:
            return f"card price still flat ({self.price_trend:+.0%}) — not late yet"
        if self.price_trend >= 0.30:
            return f"card price already +{self.price_trend:.0%} — likely LATE"
        return f"card price starting to move (+{self.price_trend:.0%}) — window closing"

    def as_alert(self) -> str:
        if self.deal_score is not None:
            hype = f"{self.interest:.0f}% hype" if self.interest is not None else "hype ?"
            head = (
                f"🔎 {self.batter.name} ({self.pos}) — DEAL {self.deal_score:.0f}/100 "
                f"(breakout {self.score:.0f}, {hype}) [{self.kind}]"
            )
            return f"{head}\n   • {self.reason}\n   • cards: {self._cards_str()}\n   • {self._trend_str()}"
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


def find_prospects(
    *,
    year: int | None = None,
    min_pa: int = 150,
    top: int = 15,
    min_score: float = 20.0,
    levels: tuple[int, ...] = (11, 12, 13, 14),
    batters: list | None = None,
) -> list[BreakoutHit]:
    """Scan the minor leagues for prospect breakouts (no price yet).

    Uses age-for-level + performance (there's no Statcast in the minors). Pass
    ``batters`` (a list of MilbBatter) to score supplied data (tests); otherwise
    fetches live from the MLB StatsAPI minor-league feeds.
    """

    from datetime import date as _date

    from prehype.sources.milb import fetch_level, prospect_reason, prospect_score

    year = year or _date.today().year
    if batters is None:
        batters = []
        for sid in levels:
            batters.extend(fetch_level(year, sid))

    hits: list[BreakoutHit] = []
    for b in batters:
        if b.pa < min_pa:
            continue
        score, kind = prospect_score(b)
        if score < min_score:
            continue
        hits.append(
            BreakoutHit(batter=b, score=score, kind=kind, age=b.age, reason=prospect_reason(b))
        )

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top]


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


def _price_asleep(pct: float | None) -> float | None:
    """0-1 'still cheap' factor from a card's price momentum.

    Flat or falling -> 1.0 (fully asleep, not late). A card already up ~50%+ ->
    ~0 (you're late). None -> None (unknown; don't penalize).
    """

    if pct is None:
        return None
    return max(0.0, min(1.0, 1.0 - pct / 0.50))


def add_prices(
    hits: list[BreakoutHit],
    *,
    client: EbayCompsClient | None = None,
    cards: tuple[str, ...] = DEFAULT_CARDS,
) -> list[BreakoutHit]:
    """Second stage: price the shortlist and apply the price-momentum gate.

    Prices the prospect cards that carry upside — Bowman Chrome 1st autos and
    rookie autos by default — then knocks down anyone whose card has *already
    moved*, even if they're quiet on Google. Google measures the public; card
    prices catch the niche collector run the hype meter misses. Re-ranks by the
    resulting deal score. Runs only on the shortlist (a handful of lookups).
    """

    client = client or EbayCompsClient()
    for h in hits:
        h.card_prices = {}
        comps_by_label: dict[str, list] = {}
        for card in cards:
            label = CARD_LABELS.get(card, card)
            query = CARD_QUERY_BUILDERS[card](h.batter.name)
            comps = trim_price_outliers(client.sold_comps(query))
            comps_by_label[label] = comps
            median = price_series_from_comps(comps).latest
            h.card_prices[label] = (median, len(comps))

        # Primary = first configured card type that returned a price.
        primary_label = None
        for card in cards:
            label = CARD_LABELS.get(card, card)
            median, count = h.card_prices[label]
            if median is not None:
                h.median_price, h.comp_count, primary_label = median, count, label
                break

        # Price-momentum gate, measured on the primary card.
        if primary_label is not None:
            h.price_trend = price_momentum_from_comps(comps_by_label[primary_label])
        base = h.sleeper_score if h.sleeper_score is not None else h.score
        asleep = _price_asleep(h.price_trend)
        h.deal_score = round(base * (asleep if asleep is not None else 1.0), 1)

    hits.sort(key=lambda h: h.rank_score, reverse=True)
    return hits
