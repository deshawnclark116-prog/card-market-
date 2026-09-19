"""Tests for the JSON API serialization and demo payload."""

import pytest

from prehype.api import DEMO_DATA, _price_status, serialize_hit
from prehype.breakouts import BreakoutHit
from prehype.sources.savant import SavantBatter


def _hit():
    b = SavantBatter("1", "Kyle Karros", 2026, 400, 0.340, 0.340, 0.50)
    h = BreakoutHit(batter=b, score=64.0, kind="leveling up", age=24, reason="jumped a lot")
    h.interest = 2.0
    h.sleeper_score = 61.0
    h.deal_score = 58.0
    h.price_trend = 0.04
    h.price_level = "cheap"
    h.card_prices = {"Bowman 1st auto": (45.0, 12), "Rookie auto": (None, 0)}
    return h


def test_price_status_thresholds():
    assert _price_status(None) == "unknown"
    assert _price_status(-0.10) == "falling"
    assert _price_status(0.0) == "flat"
    assert _price_status(0.20) == "rising"
    assert _price_status(0.55) == "hot (late)"


def test_serialize_hit_shape():
    d = serialize_hit(_hit())
    assert d["name"] == "Kyle Karros"
    assert d["position"] == "BAT"
    assert d["age"] == 24
    assert d["dealScore"] == 58
    assert d["breakoutScore"] == 64
    assert d["hypePct"] == 2
    assert d["priceStatus"] == "flat"       # trend describes momentum only
    assert d["priceLevel"] == "cheap"       # dollars describe cheapness
    assert d["cards"]["Bowman 1st auto"] == {"price": 45, "comps": 12}
    assert d["cards"]["Rookie auto"] == {"price": None, "comps": 0}


def test_demo_data_matches_schema():
    required = {
        "name", "position", "age", "dealScore", "breakoutScore",
        "sleeperScore", "hypePct", "kind", "reason", "priceTrend",
        "priceStatus", "priceLevel", "cards",
    }
    assert DEMO_DATA
    for row in DEMO_DATA:
        assert required <= set(row)
        assert row["position"] in ("BAT", "PIT")
        for card in row["cards"].values():
            assert set(card) == {"price", "comps"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
