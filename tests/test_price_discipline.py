"""Never mistake affordable cards, generic base cards or guide marks for bargains."""
from prehype.price_discipline import assess_low_entry

CARD={"manufacturer_first_bowman_auto_verified":True}

def test_under_5_item_and_under_10_delivered_is_only_low_entry():
    result=assess_low_entry(CARD,{
        "active_listing_verified":True,
        "listing_url":"https://example.com/real-active-ask",
        "item_ask_cents":300,"all_in_ask_cents":650,
        "median_cents":1000,"independent_exact_sold_comps_verified":True
    })
    assert result["low_entry_verified"]
    assert result["status"]=="LOW_ENTRY_COST_VERIFIED_UNDERVALUATION_UNKNOWN"
    assert result["item_price_usd"]==3
    assert result["all_in_price_usd"]==6.5
    assert result["discount_to_same_card_sold_median_pct"]==70
    assert result["market_lag_verified"] is False


def test_25_dollar_card_is_affordable_not_cheap():
    result=assess_low_entry(CARD,{
        "active_listing_verified":True,
        "listing_url":"https://example.com/real-active-ask",
        "item_ask_cents":1700,"all_in_ask_cents":2200
    })
    assert result["status"]=="AFFORDABLE_BUT_NOT_CHEAP_ITEM_PRICE"
    assert not result["low_entry_verified"]


def test_3_dollar_card_with_expensive_shipping_is_not_a_cheap_entry():
    result=assess_low_entry(CARD,{
        "active_listing_verified":True,
        "listing_url":"https://example.com/real-active-ask",
        "item_ask_cents":300,"all_in_ask_cents":1400,
    })
    assert result["status"]=="CHEAP_ITEM_BUT_DELIVERY_TOO_COSTLY"
    assert not result["low_entry_verified"]


def test_guide_marks_do_not_create_offer_or_verify_bowman_auto():
    assert assess_low_entry({
        "price":3.99,"manufacturer_first_bowman_auto_verified":False},
        {"median_cents":499,"comps":8}
    )["status"]=="FIRST_BOWMAN_PACK_AUTO_NOT_VERIFIED"
    assert assess_low_entry(CARD,{"median_cents":300})["status"]=="NO_VERIFIED_ACTIVE_OFFER"


def test_false_price_comparisons_have_no_proven_discount():
    result=assess_low_entry(CARD,{
        "active_listing_verified":True,
        "listing_url":"https://example.com/real-active-ask",
        "item_ask_cents":400,"all_in_ask_cents":850,
        "median_cents":2500,"independent_exact_sold_comps_verified":False,
    })
    assert result["low_entry_verified"]
    assert result["discount_to_same_card_sold_median_pct"] is None
    assert result["market_lag_verified"] is False


def test_missing_or_malformed_active_prices_fail_closed():
    for invalid in [-1, None, float("nan"),float("inf"),True, "3.2"]:
        result=assess_low_entry(CARD,{
            "active_listing_verified":True,
            "listing_url":"https://example.com/card",
            "item_ask_cents":invalid,"all_in_ask_cents":600
        })
        assert not result["low_entry_verified"]
        assert result["status"]=="MISSING_ITEM_OR_DELIVERED_PRICE"
