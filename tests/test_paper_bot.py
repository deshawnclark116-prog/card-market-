from datetime import date, timedelta
from prehype.paper_bot import _entry_cost, _liquidation_value, make_ledger, report, simulate_day, market_data_ready

DAY = date(2026, 11, 9)

def candidate(name="Test Prospect", deal=76, breakout=82, hype=3, trend=0.02):
    return {
        "name": name, "dealScore": deal, "breakoutScore": breakout,
        "hypePct": hype, "priceTrend": trend,
        "cardHypeVerified":True,
        "cards": {
            "Bowman 1st auto": {
                "manufacturer_first_bowman_auto_verified":True
            },
        },
    }

def quotes(price=1000, comps=8, age_days=1, item=300, all_in=650,
           active=True, exact=True):
    def lookup(player, card, day):
        return {
            "median_cents": price, "comps": comps,
            "last_sale": (day - timedelta(days=age_days)).isoformat(),
            "source":"verified_active_marketplace_listing",
            "active_listing_verified":active,
            "independent_exact_sold_comps_verified":exact,
            "item_ask_cents":item,"all_in_ask_cents":all_in,
            "listing_url":"https://example.com/verified-reference/123"
        }
    return lookup

def test_records_one_reference_buy_and_costs():
    state = make_ledger(DAY)
    run = simulate_day(state, [candidate()], quotes(), DAY)
    assert run["status"] == "PAPER_BUY_RECORDED"
    assert len(state["positions"]) == 1
    assert len(state["events"]) == 1
    assert state["positions"][0]["card"] == "Bowman 1st auto"
    assert state["cash_cents"] == 10_000 - 650
    assert _liquidation_value(1_000) == 500
    assert "SIMULATED" in state["positions"][0]["fill_type"]

def test_idempotent_daily_run():
    state = make_ledger(DAY)
    simulate_day(state, [candidate()], quotes(), DAY)
    cash = state["cash_cents"]
    simulate_day(state, [candidate("Another Prospect")], quotes(), DAY)
    assert len(state["events"]) == 1
    assert len(state["daily_runs"]) == 1
    assert state["cash_cents"] == cash

def test_fails_closed_without_fresh_liquid_comps():
    for lookup in [quotes(comps=4), quotes(age_days=15), lambda *args: None]:
        state = make_ledger(DAY)
        simulate_day(state, [candidate()], lookup, DAY)
        assert len(state["positions"]) == 0
        assert state["cash_cents"] == 10_000

def test_fails_closed_without_hype_price_trend_or_strong_score():
    candidates = [
        candidate("A", hype=None), candidate("B", trend=None),
        candidate("C", deal=35), candidate("D", breakout=35),
        candidate("E", hype=80), candidate("F", trend=0.4),
    ]
    state = make_ledger(DAY)
    simulate_day(state, candidates, quotes(), DAY)
    assert state["cash_cents"] == 10_000

def test_entry_budget_and_cash_never_exceeded():
    state = make_ledger(DAY)
    for n in range(10):
        day = DAY + timedelta(days=n)
        simulate_day(state, [candidate(f"Prospect {n}")], quotes(price=1900), day)
    assert len(state["positions"]) <= 5
    assert state["cash_cents"] >= 0
    assert all(p["entry_total_cents"] <= 1000 for p in state["positions"])
    assert len(state["events"]) <= 5

def test_no_buy_after_thirty_day_window():
    state = make_ledger(DAY)
    run = simulate_day(state, [candidate()], quotes(), DAY + timedelta(days=30))
    assert run["status"] == "TRIAL_COMPLETE_NO_NEW_BUYS"
    assert not state["events"]

def test_no_double_position_same_player():
    state = make_ledger(DAY)
    simulate_day(state, [candidate()], quotes(), DAY)
    simulate_day(state, [candidate()], quotes(), DAY + timedelta(days=1))
    assert len(state["positions"]) == 1

def test_report_marks_stale_as_unknown_not_profits():
    state = make_ledger(DAY)
    simulate_day(state, [candidate()], quotes(), DAY)
    next_day = report(state, DAY + timedelta(days=1))
    assert next_day["stale_or_unverified_marks"] == 0  # explicitly seven-day-old valuation window
    rep = report(state, DAY + timedelta(days=8))
    assert rep["stale_or_unverified_marks"] == 1
    assert rep["indicative_return_pct"] is None
    assert rep["number_of_paper_buys"] == 1
    assert report(state, DAY)["indicative_return_pct"] < 0

def test_no_fabricated_price_for_missing_candidates():
    state = make_ledger(DAY)
    run = simulate_day(state, [candidate()], lambda *args: None, DAY)
    assert not run["buys"]
    assert report(state, DAY)["cash_remaining_usd"] == 100


def test_market_must_have_fresh_comps_before_trial_starts():
    assert not market_data_ready([], quotes(), DAY)
    assert not market_data_ready([candidate()], quotes(comps=0), DAY)
    assert not market_data_ready([candidate()], quotes(age_days=20), DAY)
    assert market_data_ready([candidate()], quotes(), DAY)



def test_cheap_not_same_as_affordable_no_10_to_25_dollar_cards():
    for item,delivered in ((1099,1450),(1700,2000),(2499,2500)):
        state=make_ledger(DAY)
        simulate_day(state,[candidate()],quotes(item=item,all_in=delivered),DAY)
        assert not state["positions"]
        assert state["cash_cents"]==10000


def test_cheap_item_can_still_be_expensive_after_shipping():
    state=make_ledger(DAY)
    simulate_day(state,[candidate()],quotes(item=350,all_in=1250),DAY)
    assert not state["positions"]


def test_cheap_unverified_listing_or_pack_autograph_cannot_buy():
    row=candidate()
    row["cards"]["Bowman 1st auto"]["manufacturer_first_bowman_auto_verified"]=False
    state=make_ledger(DAY)
    simulate_day(state,[row],quotes(),DAY)
    assert not state["positions"]
    row=candidate()
    for lookup in [quotes(active=False),quotes(exact=False),
                   quotes(item=None),quotes(all_in=None)]:
        state=make_ledger(DAY)
        simulate_day(state,[row],lookup,DAY)
        assert not state["positions"]


def test_rejected_low_hype_evidence_must_be_explicitly_verified():
    row=candidate()
    del row["cardHypeVerified"]
    state=make_ledger(DAY)
    simulate_day(state,[row],quotes(),DAY)
    assert not state["positions"]
    assert not market_data_ready([row],quotes(),DAY)


def test_low_cost_3_dollar_manufacturer_auto_can_start_paper_trial_if_everything_verified():
    state=make_ledger(DAY)
    row=candidate()
    assert market_data_ready([row],quotes(item=300,all_in=650),DAY)
    result=simulate_day(state,[row],quotes(item=300,all_in=650),DAY)
    assert len(result["buys"])==1
    assert state["positions"][0]["entry_total_cents"]==650
    assert state["positions"][0]["entry_basis"]=="VERIFIED_ACTIVE_FIRST_BOWMAN_AUTO_LISTING_PAPER_ONLY"
