"""Low-entry 1st Bowman auto *acquisition* screen, separate from affordability.

A $25 budget is not a definition of CHEAP. No card can be labeled cheaply
BUYABLE without a verified pack-issued 1st Bowman autograph identity and an
individually identified ACTIVE offer including its item price, shipping/tax.

This tests low acquisition cost only; it does not prove low collector attention,
future breakout, a discount to fair value, or liquidity. The latter are other
independent investment gates.
"""
from __future__ import annotations

import math

CHEAP_CARD_MAX_CENTS = 500        # target at most $5 for the actual card
CHEAP_ALL_IN_MAX_CENTS = 1000     # no more than $10 after delivery/taxes
CHEAP_CARD_IDENTITY_KEY = "manufacturer_first_bowman_auto_verified"


def _cents(value):
    """Only accept explicit integral nonnegative amounts; never vendor guides."""
    if isinstance(value, bool):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(v) or v < 0 or not v.is_integer():
        return None
    return int(v)


def assess_low_entry(card_meta, quote):
    """Return a transparent affordability-vs-cheapness finding.

    Unverified cards and unavailable active offers remain UNKNOWN, never 'cheap'.
    A buyer may still lose money on a genuine $3 first Bowman auto.
    """
    card_meta=card_meta if isinstance(card_meta,dict) else {}
    quote=quote if isinstance(quote,dict) else {}
    record={
        "status":"NOT_VERIFIED",
        "low_entry_verified":False,
        "item_price_usd":None,
        "all_in_price_usd":None,
        "max_item_usd":CHEAP_CARD_MAX_CENTS/100,
        "max_all_in_usd":CHEAP_ALL_IN_MAX_CENTS/100,
        "same_card_sold_median_usd":None,
        "discount_to_same_card_sold_median_pct":None,
        "market_lag_verified":False,
        "warning":"A low dollar price alone is not a bargain, or proof of low card-market hype.",
    }
    if card_meta.get(CHEAP_CARD_IDENTITY_KEY) is not True:
        record["status"]="FIRST_BOWMAN_PACK_AUTO_NOT_VERIFIED"
        return record
    if not (quote.get("active_listing_verified") is True
            and isinstance(quote.get("listing_url"),str)
            and quote["listing_url"].startswith("https://")):
        record["status"]="NO_VERIFIED_ACTIVE_OFFER"
        return record
    item=_cents(quote.get("item_ask_cents"))
    total=_cents(quote.get("all_in_ask_cents"))
    if item is None or total is None or total < item:
        record["status"]="MISSING_ITEM_OR_DELIVERED_PRICE"
        return record
    record["item_price_usd"]=round(item/100,2)
    record["all_in_price_usd"]=round(total/100,2)
    median=_cents(quote.get("median_cents"))
    if median is not None and median>0 and quote.get("independent_exact_sold_comps_verified") is True:
        record["same_card_sold_median_usd"]=round(median/100,2)
        record["discount_to_same_card_sold_median_pct"]=round(100*(1-item/median),1)
    if item>CHEAP_CARD_MAX_CENTS:
        record["status"]="AFFORDABLE_BUT_NOT_CHEAP_ITEM_PRICE"
    elif total>CHEAP_ALL_IN_MAX_CENTS:
        record["status"]="CHEAP_ITEM_BUT_DELIVERY_TOO_COSTLY"
    else:
        record["status"]="LOW_ENTRY_COST_VERIFIED_UNDERVALUATION_UNKNOWN"
        record["low_entry_verified"]=True
    return record
