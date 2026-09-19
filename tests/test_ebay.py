"""Tests for the eBay comps parser and series builders.

Live eBay is blocked from CI/datacenter IPs, so parsing is verified against a
saved HTML fixture that mirrors eBay's real sold-listings DOM.
"""

import os
from datetime import date

import pytest

from prehype.models import Candidate
from prehype.sources.ebay import (
    EbayCompsClient,
    SoldComp,
    CompsBackend,
    MarketplaceInsightsBackend,
    ScrapeBackend,
    build_sold_url,
    default_backend,
    parse_sold_comps,
    price_series_from_comps,
    trim_price_outliers,
    velocity_series_from_comps,
)
from prehype.sources.watchlist import WatchlistSource

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ebay_sold_sample.html")


def _load():
    with open(FIXTURE, encoding="utf-8") as f:
        return f.read()


def test_parse_skips_placeholder_and_extracts_comps():
    comps = parse_sold_comps(_load())
    # 6 <li> in the fixture, but "Shop on eBay" placeholder is skipped.
    assert len(comps) == 5
    assert all(isinstance(c, SoldComp) for c in comps)


def test_parse_reads_price_date_title_url():
    comps = parse_sold_comps(_load())
    first = comps[0]
    assert first.price == 210.00
    assert first.sold_on == date(2024, 3, 3)
    assert "Julio Rodriguez" in first.title
    assert first.item_url and first.item_url.startswith("https://www.ebay.com/itm/")


def test_parse_price_range_takes_low_end():
    comps = parse_sold_comps(_load())
    ranged = [c for c in comps if c.sold_on == date(2024, 3, 5)]
    assert ranged and ranged[0].price == 1250.00


def test_parse_decodes_html_entities_in_title():
    comps = parse_sold_comps(_load())
    assert any("& case" in c.title for c in comps)


def test_trim_price_outliers_drops_wrong_variant():
    comps = parse_sold_comps(_load())  # includes a $1,250 range outlier
    trimmed = trim_price_outliers(comps, factor=3.0)
    prices = [c.price for c in trimmed]
    assert 1250.0 not in prices
    assert 210.0 in prices and 255.0 in prices


def test_default_backend_picks_from_env(monkeypatch):
    monkeypatch.delenv("EBAY_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("EBAY_PROXY_URL", raising=False)
    assert isinstance(default_backend(), ScrapeBackend)

    monkeypatch.setenv("EBAY_PROXY_URL", "http://proxy:8080")
    b = default_backend()
    assert isinstance(b, ScrapeBackend) and b.proxy_url == "http://proxy:8080"

    monkeypatch.setenv("EBAY_OAUTH_TOKEN", "tok")
    assert isinstance(default_backend(), MarketplaceInsightsBackend)


def test_build_sold_url_has_sold_filters():
    url = build_sold_url("Julio Rodriguez PSA 10", ipg=120)
    assert "LH_Sold=1" in url and "LH_Complete=1" in url and "_ipg=120" in url


def test_price_series_is_weekly_median():
    comps = parse_sold_comps(_load())
    series = price_series_from_comps(comps, weeks=8)
    assert len(series) >= 1
    # Prices are all positive and the series is chronologically ordered.
    assert series.points == sorted(series.points, key=lambda p: p.on)
    assert all(p.value > 0 for p in series.points)


def test_velocity_series_counts_sales_per_week():
    comps = parse_sold_comps(_load())
    vel = velocity_series_from_comps(comps, weeks=8, saturation=25)
    assert len(vel) >= 1
    assert all(0 <= p.value <= 100 for p in vel.points)


class _FixtureBackend(CompsBackend):
    """A backend that returns comps parsed from the saved fixture (no network)."""

    def sold_comps(self, query, *, max_results=240):
        return parse_sold_comps(_load())[:max_results]


def test_client_caches_and_returns_comps(tmp_path):
    client = EbayCompsClient(backend=_FixtureBackend(), cache_dir=str(tmp_path))
    comps = client.sold_comps("anything")
    assert len(comps) == 5
    # Second call should hit cache and still round-trip cleanly.
    again = client.sold_comps("anything")
    assert [c.to_json() for c in again] == [c.to_json() for c in comps]


def test_watchlist_source_builds_priced_candidates(tmp_path):
    wl = tmp_path / "wl.json"
    wl.write_text(
        """
        {"players": [
          {"player_id": "jrod", "name": "Julio Rodriguez", "sport": "MLB",
           "ebay_query": "2022 Topps Chrome Julio Rodriguez RC PSA 10",
           "performance": [40, 48, 56, 65, 74, 82], "age": 23}
        ]}
        """,
        encoding="utf-8",
    )
    client = EbayCompsClient(backend=_FixtureBackend(), cache_dir=str(tmp_path / "c"))
    src = WatchlistSource(str(wl), client=client)
    cands = list(src.candidates())
    assert len(cands) == 1
    c = cands[0]
    assert isinstance(c, Candidate)
    assert c.price.latest and c.price.latest > 0   # real eBay price wired in
    assert len(c.attention) >= 1                    # velocity wired in


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
