"""Tests for the Statcast breakout engine.

The engine scores IMPROVEMENT + youth (not raw skill), so sleepers rank above
famous stars. These tests pin that behavior down.
"""

import os

import pytest

from prehype.breakouts import add_hype, add_prices, find_breakouts
from prehype.sources.ebay import CompsBackend, EbayCompsClient, SoldComp
from prehype.sources.savant import SavantBatter, breakout_score, parse_expected_stats

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "savant_expected_sample.csv")


def _mk(pid, now_woba, pa=400, est_slg=0.45, name=None, player_type="batter"):
    return SavantBatter(
        player_id=pid,
        name=name or pid,
        year=2026,
        pa=pa,
        woba=now_woba,
        est_woba=now_woba,
        est_slg=est_slg,
        player_type=player_type,
    )


def test_parse_reads_names_and_stats():
    with open(FIXTURE, encoding="utf-8") as f:
        batters = parse_expected_stats(f.read(), 2024)
    assert len(batters) == 5
    spring = next(b for b in batters if b.player_id == "900001")
    assert spring.name == "Spring Coiled"      # "Coiled, Spring" -> "Spring Coiled"
    assert spring.est_woba == 0.400


def test_sleeper_outranks_star_and_flat_average():
    # Young player who jumped from below-average to good.
    sleeper_now = _mk("sleeper", 0.360, pa=400)
    sleeper_prior = _mk("sleeper", 0.300, pa=400)
    sleeper, kind = breakout_score(sleeper_now, sleeper_prior, age=22)

    # Established star: already elite last year, no real jump, older.
    star_now = _mk("star", 0.415, pa=600)
    star_prior = _mk("star", 0.410, pa=600)
    star, _ = breakout_score(star_now, star_prior, age=30)

    # Solid but flat veteran: no improvement.
    flat_now = _mk("flat", 0.316, pa=500)
    flat_prior = _mk("flat", 0.315, pa=500)
    flat, _ = breakout_score(flat_now, flat_prior, age=29)

    assert kind == "leveling up"
    assert sleeper > star
    assert sleeper > flat
    assert star < 25          # the famous-star profile scores low here


def test_youth_boosts_identical_jump():
    now = _mk("p", 0.355)
    prior = _mk("p", 0.305)
    young, _ = breakout_score(now, prior, age=21)
    old, _ = breakout_score(now, prior, age=30)
    assert young > old


def test_pitcher_breakout_rewards_a_drop_in_contact_allowed():
    # Pitcher: xwOBA-against dropped a lot (got harder to hit), from a hittable
    # prior, and he's young -> strong breakout.
    now = _mk("nasty", 0.285, pa=400, player_type="pitcher")
    prior = _mk("nasty", 0.345, pa=400, player_type="pitcher")
    good, kind = breakout_score(now, prior, age=23)

    # Pitcher who got WORSE (contact allowed rose) should score ~0.
    worse_now = _mk("worse", 0.345, pa=400, player_type="pitcher")
    worse_prior = _mk("worse", 0.285, pa=400, player_type="pitcher")
    worse, _ = breakout_score(worse_now, worse_prior, age=23)

    assert kind == "leveling up"
    assert good > 30
    assert good > worse
    assert worse < 10


def test_multi_scan_merges_batters_and_pitchers():
    from prehype.breakouts import find_breakouts

    bat = find_breakouts(
        batters=[_mk("bat", 0.360, pa=400)],
        prior=[_mk("bat", 0.300, pa=400)],
        ages={"bat": 23}, min_pa=150, min_score=0.0, player_type="batter",
    )
    pit = find_breakouts(
        batters=[_mk("pit", 0.285, pa=400, player_type="pitcher")],
        prior=[_mk("pit", 0.345, pa=400, player_type="pitcher")],
        ages={"pit": 23}, min_pa=150, min_score=0.0, player_type="pitcher",
    )
    assert bat and pit
    assert bat[0].pos == "BAT"
    assert pit[0].pos == "PIT"


def test_new_face_is_emerging():
    now = _mk("rook", 0.370, pa=250)
    score, kind = breakout_score(now, prior=None, age=22)
    assert kind == "emerging"
    assert score > 0


def test_find_breakouts_ranks_sleeper_first_and_filters_min_pa():
    current = [
        _mk("sleeper", 0.360, pa=400),
        _mk("star", 0.415, pa=600),
        _mk("smallsample", 0.400, pa=80),
    ]
    prior = [
        _mk("sleeper", 0.300, pa=400),
        _mk("star", 0.410, pa=600),
    ]
    ages = {"sleeper": 22, "star": 30, "smallsample": 24}
    hits = find_breakouts(
        batters=current, prior=prior, ages=ages, min_pa=150, top=10, min_score=0.0
    )
    ids = [h.batter.player_id for h in hits]
    assert "smallsample" not in ids          # filtered by min_pa
    assert hits[0].batter.player_id == "sleeper"


def test_add_hype_demotes_the_famous_name():
    # Two identical breakouts; one is heavily searched, one is unknown.
    current = [_mk("famous", 0.360, pa=400), _mk("unknown", 0.360, pa=400)]
    prior = [_mk("famous", 0.300, pa=400), _mk("unknown", 0.300, pa=400)]
    ages = {"famous": 23, "unknown": 23}
    hits = find_breakouts(
        batters=current, prior=prior, ages=ages, min_pa=150, top=10, min_score=0.0
    )
    # famous: 80% of a star's searches; unknown: 1%.
    hits = add_hype(hits, interest={"famous": 80.0, "unknown": 1.0})
    assert hits[0].batter.player_id == "unknown"       # sleeper rises to the top
    assert hits[0].sleeper_score > hits[1].sleeper_score
    famous = next(h for h in hits if h.batter.player_id == "famous")
    assert famous.sleeper_score < famous.score          # hype knocked it down


class _FakeEbay(CompsBackend):
    def sold_comps(self, query, *, max_results=240):
        from datetime import date
        return [SoldComp(price=25.0, sold_on=date(2026, 3, 10), title=query)]


class _PricedEbay(CompsBackend):
    """Flat price series; 'cheap' names ~$10, 'pricey' names ~$120."""

    def sold_comps(self, query, *, max_results=240):
        from datetime import date, timedelta
        start = date(2026, 3, 1)
        price = 120.0 if query.lower().startswith("pricey") else 10.0
        return [
            SoldComp(price=price, sold_on=start + timedelta(weeks=i), title=query)
            for i in range(6) for _ in range(3)
        ]


def test_absolute_price_gate_prefers_the_actually_cheap_card(tmp_path):
    # Two identical sleepers, both flat price — but one card is $10, one is $120.
    current = [_mk("cheap", 0.360, pa=400, name="Cheap Guy"),
               _mk("pricey", 0.360, pa=400, name="Pricey Guy")]
    prior = [_mk("cheap", 0.300, pa=400), _mk("pricey", 0.300, pa=400)]
    hits = find_breakouts(
        batters=current, prior=prior, ages={"cheap": 23, "pricey": 23},
        min_pa=150, top=10, min_score=0.0,
    )
    add_hype(hits, interest={"Cheap Guy": 3.0, "Pricey Guy": 3.0})
    client = EbayCompsClient(backend=_PricedEbay(), cache_dir=str(tmp_path))
    priced = add_prices(hits, client=client)

    cheap = next(h for h in priced if h.batter.player_id == "cheap")
    pricey = next(h for h in priced if h.batter.player_id == "pricey")
    assert cheap.price_level == "dirt cheap"
    assert pricey.price_level == "pricey"
    assert cheap.deal_score > pricey.deal_score   # dollars matter now
    assert priced[0].batter.player_id == "cheap"


class _TrendEbay(CompsBackend):
    """Returns a flat price series for 'flat' names, a rising one for 'hot' names."""

    def sold_comps(self, query, *, max_results=240):
        from datetime import date, timedelta
        start = date(2026, 3, 1)
        rising = query.lower().startswith("hot")
        weekly = [20, 21, 20, 22, 40, 55, 70, 85] if rising else [20, 21, 20, 22, 21, 20, 22, 21]
        comps = []
        for i, price in enumerate(weekly):
            wk = start + timedelta(weeks=i)
            # a few sales per week so weekly medians are stable
            comps += [SoldComp(price=float(price), sold_on=wk, title=query) for _ in range(3)]
        return comps


def test_price_momentum_gate_demotes_a_card_thats_already_running(tmp_path):
    # Two identical sleepers; one's card is flat, the other's is already ripping.
    current = [
        _mk("flat", 0.360, pa=400, name="Flat Guy"),
        _mk("hot", 0.360, pa=400, name="Hot Guy"),
    ]
    prior = [_mk("flat", 0.300, pa=400), _mk("hot", 0.300, pa=400)]
    ages = {"flat": 23, "hot": 23}
    hits = find_breakouts(
        batters=current, prior=prior, ages=ages, min_pa=150, top=10, min_score=0.0
    )
    # Same hype for both, so only the card trend can separate them.
    add_hype(hits, interest={"Flat Guy": 3.0, "Hot Guy": 3.0})
    client = EbayCompsClient(backend=_TrendEbay(), cache_dir=str(tmp_path))
    priced = add_prices(hits, client=client)

    flat = next(h for h in priced if h.batter.player_id == "flat")
    hot = next(h for h in priced if h.batter.player_id == "hot")
    assert hot.price_trend > 0.30            # detected the run-up
    assert (flat.price_trend or 0) <= 0.05   # flat card stays flat
    assert flat.deal_score > hot.deal_score  # the still-cheap one wins
    assert priced[0].batter.player_id == "flat"


def test_add_prices_fills_bowman_and_rookie_auto(tmp_path):
    current = [_mk("sleeper", 0.360, pa=400)]
    prior = [_mk("sleeper", 0.300, pa=400)]
    hits = find_breakouts(
        batters=current, prior=prior, ages={"sleeper": 22}, min_pa=150, min_score=0.0
    )
    client = EbayCompsClient(backend=_FakeEbay(), cache_dir=str(tmp_path))
    priced = add_prices(hits, client=client)
    cards = priced[0].card_prices
    assert "Bowman 1st auto" in cards and "Rookie auto" in cards
    assert cards["Bowman 1st auto"][0] == 25.0
    assert priced[0].median_price == 25.0   # primary = first card type with a price


def test_starters_only_drops_relievers():
    pit_start = _mk("starter", 0.285, pa=400, player_type="pitcher")
    pit_relief = _mk("reliever", 0.285, pa=400, player_type="pitcher")
    prior = [
        _mk("starter", 0.345, pa=400, player_type="pitcher"),
        _mk("reliever", 0.345, pa=400, player_type="pitcher"),
    ]
    roles = {"starter": True, "reliever": False}
    hits = find_breakouts(
        batters=[pit_start, pit_relief], prior=prior,
        ages={"starter": 23, "reliever": 27}, roles=roles,
        min_pa=150, min_score=0.0, player_type="pitcher", starters_only=True,
    )
    ids = [h.batter.player_id for h in hits]
    assert "starter" in ids
    assert "reliever" not in ids


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
