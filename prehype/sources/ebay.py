"""Real eBay sold-comps: the single biggest signal upgrade.

eBay sold/completed listings give us two things at once:

* **Price** — what cards actually trade for (weekly median -> price momentum +
  cheapness).
* **Sales velocity** — how many sold this week vs last. This is the *best early
  attention signal there is*: velocity spikes before price does.

Two important realities this module is built around:

1. **eBay blocks sold-listing scraping from datacenter/cloud IPs** (you'll get
   HTTP 403). The scrape backend works from a residential IP (your own
   machine) or through a scraping proxy. From a blocked host it fails
   gracefully and the pipeline keeps running.
2. **The sanctioned, un-blockable path is eBay's official API** (Marketplace
   Insights `item_sales/search`). Supply an OAuth token and the API backend
   returns the same comps with no IP games.

Both backends produce the same :class:`SoldComp` list, so the rest of the
system doesn't care which one you use.
"""

from __future__ import annotations

import abc
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from statistics import median

from prehype.models import AttentionSeries, PriceSeries

_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


@dataclass
class SoldComp:
    """One sold listing."""

    price: float
    sold_on: date
    title: str
    item_url: str | None = None

    def to_json(self) -> dict:
        d = asdict(self)
        d["sold_on"] = self.sold_on.isoformat()
        return d

    @classmethod
    def from_json(cls, d: dict) -> "SoldComp":
        return cls(
            price=float(d["price"]),
            sold_on=date.fromisoformat(d["sold_on"]),
            title=d["title"],
            item_url=d.get("item_url"),
        )


# --------------------------------------------------------------------------- #
# HTML parsing (used by the scrape backend; kept standalone so it's testable
# against a saved fixture with no network).
# --------------------------------------------------------------------------- #

_PRICE_RE = re.compile(r"\$\s*([\d,]+(?:\.\d{2})?)")
_DATE_RE = re.compile(r"Sold\s+([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})")
_TITLE_RE = re.compile(r"s-item__title[^>]*>(.*?)</(?:div|h3|span)>", re.DOTALL)
_URL_RE = re.compile(r'href="(https://www\.ebay\.com/itm/[^"?#]+)')
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    text = _TAG_RE.sub(" ", text)
    text = text.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
    return re.sub(r"\s+", " ", text).strip()


def _parse_price(block: str) -> float | None:
    """Return the low end of the price (ranges show as '$X to $Y')."""

    m = _PRICE_RE.search(block)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _parse_date(block: str) -> date | None:
    m = _DATE_RE.search(block)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%b %d, %Y").date()
    except ValueError:
        return None


def parse_sold_comps(html: str) -> list[SoldComp]:
    """Parse eBay sold-listings HTML into comps.

    Resilient by design: skips the placeholder "Shop on eBay" card and any item
    missing a price or sold date, rather than throwing. eBay changes its markup
    periodically — if this ever returns empty on a page that clearly has
    results, the CSS class names below are the thing to update.
    """

    comps: list[SoldComp] = []
    # Each result's content lives after an 's-item__info' marker.
    blocks = html.split("s-item__info")[1:]
    for block in blocks:
        price = _parse_price(block)
        sold_on = _parse_date(block)
        if price is None or sold_on is None:
            continue
        tm = _TITLE_RE.search(block)
        title = _clean(tm.group(1)) if tm else ""
        if not title or "Shop on eBay" in title:
            continue
        um = _URL_RE.search(block)
        comps.append(
            SoldComp(price=price, sold_on=sold_on, title=title, item_url=um.group(1) if um else None)
        )
    return comps


def build_sold_url(query: str, *, ipg: int = 240, category: int | None = None) -> str:
    """Build an eBay completed+sold search URL."""

    params = {
        "_nkw": query,
        "LH_Sold": "1",
        "LH_Complete": "1",
        "_ipg": str(ipg),  # items per page (60/120/240)
    }
    if category is not None:
        params["_sacat"] = str(category)
    return "https://www.ebay.com/sch/i.html?" + urllib.parse.urlencode(params)


# --------------------------------------------------------------------------- #
# Backends: where comps actually come from.
# --------------------------------------------------------------------------- #


class CompsBackend(abc.ABC):
    """Fetches sold comps for a search query."""

    @abc.abstractmethod
    def sold_comps(self, query: str, *, max_results: int = 240) -> list[SoldComp]:
        raise NotImplementedError


class ScrapeBackend(CompsBackend):
    """Fetches and parses eBay's sold-listings HTML.

    NOTE: eBay 403s scraper traffic from datacenter IPs. Run this from a
    residential IP or route ``opener`` through a scraping proxy. On any failure
    it returns ``[]`` so the pipeline degrades gracefully.
    """

    def __init__(
        self,
        *,
        user_agent: str = _DEFAULT_UA,
        timeout: float = 20.0,
        ipg: int = 240,
        category: int | None = None,
        proxy_url: str | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.ipg = ipg
        self.category = category
        self.proxy_url = proxy_url

    def _get(self, url: str) -> str | None:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            if self.proxy_url:
                handler = urllib.request.ProxyHandler(
                    {"http": self.proxy_url, "https": self.proxy_url}
                )
                opener = urllib.request.build_opener(handler)
            else:
                opener = urllib.request.build_opener()
            req = urllib.request.Request(url, headers=headers)
            with opener.open(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, ValueError):
            return None

    def sold_comps(self, query: str, *, max_results: int = 240) -> list[SoldComp]:
        url = build_sold_url(query, ipg=min(self.ipg, max_results), category=self.category)
        html = self._get(url)
        if not html:
            return []
        return parse_sold_comps(html)[:max_results]


class MarketplaceInsightsBackend(CompsBackend):
    """Official eBay Marketplace Insights API — the un-blockable path.

    Requires an OAuth application token with the
    ``buy.marketplace.insights`` scope (approval needed from eBay). Pass the
    token directly or set ``EBAY_OAUTH_TOKEN``. This backend is not exercised in
    CI (no token), but is wired and ready.
    """

    _ENDPOINT = "https://api.ebay.com/buy/marketplace_insights/v1_beta/item_sales/search"

    def __init__(
        self,
        token: str | None = None,
        *,
        marketplace: str = "EBAY_US",
        timeout: float = 20.0,
    ) -> None:
        self.token = token or os.environ.get("EBAY_OAUTH_TOKEN")
        self.marketplace = marketplace
        self.timeout = timeout

    def sold_comps(self, query: str, *, max_results: int = 200) -> list[SoldComp]:
        if not self.token:
            return []
        params = urllib.parse.urlencode({"q": query, "limit": str(min(max_results, 200))})
        req = urllib.request.Request(
            f"{self._ENDPOINT}?{params}",
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError):
            return []

        comps: list[SoldComp] = []
        for item in data.get("itemSales", []):
            price_info = item.get("lastSoldPrice") or {}
            value = price_info.get("value")
            sold_str = item.get("lastSoldDate")
            if value is None or not sold_str:
                continue
            try:
                sold_on = datetime.fromisoformat(sold_str.replace("Z", "+00:00")).date()
                price = float(value)
            except (ValueError, TypeError):
                continue
            comps.append(
                SoldComp(
                    price=price,
                    sold_on=sold_on,
                    title=item.get("title", ""),
                    item_url=item.get("itemWebUrl"),
                )
            )
        return comps


# --------------------------------------------------------------------------- #
# Client: caching wrapper + series builders.
# --------------------------------------------------------------------------- #


class EbayCompsClient:
    """Sold-comps with on-disk caching, plus helpers to build signal series."""

    def __init__(
        self,
        backend: CompsBackend | None = None,
        *,
        cache_dir: str | None = None,
        ttl_seconds: float = 6 * 3600,
    ) -> None:
        self.backend = backend or ScrapeBackend()
        self.cache_dir = cache_dir or os.path.join(
            os.path.expanduser("~"), ".cache", "prehype", "ebay"
        )
        self.ttl_seconds = ttl_seconds

    def _cache_path(self, query: str) -> str:
        key = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"{key}.json")

    def _read_cache(self, path: str) -> list[SoldComp] | None:
        try:
            if not os.path.exists(path):
                return None
            if time.time() - os.path.getmtime(path) > self.ttl_seconds:
                return None
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            return [SoldComp.from_json(d) for d in raw]
        except (OSError, ValueError, KeyError):
            return None

    def _write_cache(self, path: str, comps: list[SoldComp]) -> None:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump([c.to_json() for c in comps], f)
        except OSError:
            pass

    def sold_comps(
        self, query: str, *, max_results: int = 240, use_cache: bool = True
    ) -> list[SoldComp]:
        path = self._cache_path(query)
        if use_cache:
            cached = self._read_cache(path)
            if cached is not None:
                return cached
        comps = self.backend.sold_comps(query, max_results=max_results)
        if comps:
            self._write_cache(path, comps)
        return comps


# --------------------------------------------------------------------------- #
# Comps -> signal series
# --------------------------------------------------------------------------- #


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def trim_price_outliers(comps: list[SoldComp], *, factor: float = 3.0) -> list[SoldComp]:
    """Drop comps whose price is wildly off the overall median.

    A loose eBay query pulls in the wrong card — autos, refractors, lots, the
    occasional typo listing — and one $1,250 sale in a $250 population wrecks
    the median. This keeps comps within ``[median/factor, median*factor]``.
    Tighten your ``ebay_query`` first; this is the safety net.
    """

    if len(comps) < 4:
        return comps
    med = median(c.price for c in comps)
    if med <= 0:
        return comps
    lo, hi = med / factor, med * factor
    return [c for c in comps if lo <= c.price <= hi]


def price_series_from_comps(comps: list[SoldComp], *, weeks: int = 8) -> PriceSeries:
    """Weekly median sold price over the trailing ``weeks`` (oldest first)."""

    if not comps:
        return PriceSeries.of([])
    buckets: dict[date, list[float]] = {}
    for c in comps:
        buckets.setdefault(_week_start(c.sold_on), []).append(c.price)
    weekly = sorted(buckets.items())[-weeks:]
    return PriceSeries.of([(wk, median(prices)) for wk, prices in weekly])


def price_momentum_from_comps(comps: list[SoldComp], *, weeks: int = 8) -> float | None:
    """Recent price change of a card, as a fraction (e.g. 0.30 == up 30%).

    Compares the recent half of the weekly-median series to the earlier half.
    Positive = the card is already climbing (you may be late); <= 0 = still flat
    or falling (still asleep). Returns None when there aren't enough weeks of
    sales to judge (an illiquid card), so callers can treat it as "unknown"
    rather than penalize it.
    """

    vals = price_series_from_comps(comps, weeks=weeks).values
    if len(vals) < 3:
        return None
    mid = len(vals) // 2
    earlier, recent = vals[:mid], vals[mid:]
    base = sum(earlier) / len(earlier)
    if base <= 0:
        return None
    return (sum(recent) / len(recent) - base) / base


def velocity_series_from_comps(
    comps: list[SoldComp], *, weeks: int = 8, saturation: int = 25
) -> AttentionSeries:
    """Weekly sales *count* as a 0-100 attention index (oldest first).

    ``saturation`` is the weekly sold-count that maps to ~100 — tune per how
    liquid your reference card is. Rising velocity from a low base is the
    earliest sign the crowd is arriving.
    """

    if not comps:
        return AttentionSeries.of([])
    counts: dict[date, int] = {}
    for c in comps:
        counts[_week_start(c.sold_on)] = counts.get(_week_start(c.sold_on), 0) + 1
    weekly = sorted(counts.items())[-weeks:]
    return AttentionSeries.of(
        [(wk, min(100.0, n / saturation * 100.0)) for wk, n in weekly]
    )
