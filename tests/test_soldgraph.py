"""All deterministic: no third-party key and no network calls."""
import io
import json
from datetime import date, timedelta

from prehype.sources.soldgraph import (
    SoldgraphClient, SoldgraphQuotes, card_signature, compute_quote,
    compute_variant_mark, safe_ebay_listing_url,
)
from prehype.paper_bot import _entry_cost, make_ledger, market_data_ready, simulate_day

DAY = date(2026,11,9)
NAME = "Walbert Urena"
CARD = "Bowman 1st auto"
TITLE = "2025 Bowman Chrome 1st Walbert Urena Auto #CPA-WU"


def sold(price, days, title=TITLE, best_offer=False):
    return {
        "title":title,
        "displayed_price":{"amount":price,"currency":"USD"},
        "displayed_shipping":{"amount":0,"currency":"USD"},
        "sold_date":(DAY-timedelta(days=days)).isoformat(),
        "best_offer_accepted":best_offer,
    }


def offered(price=10, shipping=2, title=TITLE):
    return {
        "title":title,
        "displayed_price":{"amount":price,"currency":"USD"},
        "displayed_shipping":{"amount":shipping,"currency":"USD"},
        "format":"fixed_price",
        "link":"https://www.ebay.com/itm/1234567890",
    }


SALES = [sold(27,30), sold(28,25), sold(29,15), sold(29,7), sold(30,1)]


def test_excludes_wrong_player_grade_parallel_and_nonauto():
    assert card_signature(TITLE,NAME,CARD) == "2025|bowman-chrome-1st|cpawu"
    assert card_signature(TITLE.replace("Walbert Urena","Other Player"),NAME,CARD) is None
    assert card_signature(TITLE+" PSA 10",NAME,CARD) is None
    assert card_signature(TITLE+" Refractor",NAME,CARD) is None
    assert card_signature(TITLE+" /99",NAME,CARD) is None
    assert card_signature(TITLE.replace(" Auto"," Base"),NAME,CARD) is None
    assert card_signature(TITLE.replace("2025","2024"),NAME,CARD) != card_signature(TITLE,NAME,CARD)
    assert card_signature(TITLE.replace("#CPA-WU","#CPA-DIFF"),NAME,CARD) != card_signature(TITLE,NAME,CARD)


def test_requires_matching_five_sales_two_periods_and_live_offer():
    q=compute_quote(SALES,[offered()],NAME,CARD,DAY)
    assert q is not None
    assert q["median_cents"] == 2900
    assert q["comps"] == 5
    assert q["all_in_ask_cents"] == 1272
    assert q["listing_url"] == "https://www.ebay.com/itm/1234567890"
    assert q["net_resale_margin_cents"] >= 200
    assert 0 < q["price_trend"] < 0.15


def test_not_bought_with_no_active_offer_or_unknown_shipping():
    assert compute_quote(SALES,[],NAME,CARD,DAY) is None
    r=offered()
    r["displayed_shipping"]=None
    assert compute_quote(SALES,[r],NAME,CARD,DAY) is None
    assert compute_quote(SALES,[offered(price=23)],NAME,CARD,DAY) is None
    auction=offered()
    auction["format"]="auction"
    assert compute_quote(SALES,[auction],NAME,CARD,DAY) is None


def test_sold_comps_reject_best_offers_mixed_variants_and_temporal_gaps():
    assert compute_quote(SALES[:4],[offered()],NAME,CARD,DAY) is None
    assert compute_quote(SALES[:-1]+[sold(30,1,best_offer=True)],
                         [offered()],NAME,CARD,DAY) is None
    mixed=SALES[:4]+[sold(30,1,title=TITLE+" PSA 10")]
    assert compute_quote(mixed,[offered()],NAME,CARD,DAY) is None
    same_week=[sold(27,4),sold(28,3),sold(28,2),sold(29,1),sold(30,0)]
    assert compute_quote(same_week,[offered()],NAME,CARD,DAY) is None


def test_no_untrusted_external_link_or_other_currencies():
    assert not safe_ebay_listing_url("https://bad.example/itm/123")
    assert not safe_ebay_listing_url("http://www.ebay.com/itm/123")
    assert not safe_ebay_listing_url("https://www.ebay.com.evil.test/itm/123")
    assert safe_ebay_listing_url("https://www.ebay.com/itm/123")
    r=offered()
    r["link"]="https://evil.test/itm/123"
    assert compute_quote(SALES,[r],NAME,CARD,DAY) is None
    r=offered()
    r["displayed_price"]["currency"]="CAD"
    assert compute_quote(SALES,[r],NAME,CARD,DAY) is None


def test_reprice_existing_matching_variant_without_active_listing():
    key=card_signature(TITLE,NAME,CARD)
    mark=compute_variant_mark(SALES,NAME,CARD,key,DAY)
    assert mark and mark["median_cents"]==2900
    assert mark["source"]=="soldgraph_mark"
    assert compute_variant_mark(SALES[:3],NAME,CARD,key,DAY) is None


class Reply:
    def __init__(self,payload):
        self.bytes=io.BytesIO(json.dumps(payload).encode("utf-8"))
    def __enter__(self):
        return self
    def __exit__(self,*args):
        return False
    def read(self,*args):
        return self.bytes.read(*args)


def test_pending_api_job_is_long_polled_safely():
    calls=[]
    def opener(req,timeout=None):
        calls.append(req.full_url)
        if len(calls)==1:
            return Reply({"status":"pending","poll_url":"/v1/jobs/valid-123"})
        return Reply({"status":"complete","result":{
            "provider":"ebay","country":"us","data":[{"title":"some item"}]}})
    client=SoldgraphClient(key="test-no-real-secret",opener=opener,max_searches=1)
    assert client.search("sold","test query")==[{"title":"some item"}]
    assert client.searches_used==1
    assert len(calls)==2
    assert "/v1/jobs/valid-123?wait=20" in calls[1]
    assert client.search("listings","test query") is None
    assert len(calls)==2


class FakeClient:
    def __init__(self):
        self.key="test"
        self.last_error=None
        self.searches_used=0
        self.kinds=[]
    def search(self,kind,query):
        self.kinds.append(kind)
        self.searches_used+=1
        return SALES if kind=="sold" else [offered()]


def test_one_pair_a_day_and_ledger_can_buy_actual_listed_card():
    client=FakeClient()
    monitor={"schema":1,"attempts":{},"last_provider_error":None,"requests_total":0}
    lookup=SoldgraphQuotes(client=client,monitor=monitor)
    c={"name":NAME,"breakoutScore":90,"sleeperScore":90,
       "hypePct":1,"dealScore":85,"priceTrend":.05,
       "cards":{CARD:{}}}
    lookup.prime([c],DAY)
    assert client.kinds == ["sold","listings"]
    assert monitor["requests_total"]==2
    assert market_data_ready([c],lookup.lookup,DAY)
    state=make_ledger(DAY)
    run=simulate_day(state,[c],lookup.lookup,DAY)
    assert run["status"]=="PAPER_BUY_RECORDED"
    assert state["positions"][0]["entry_total_cents"]==1272
    assert state["positions"][0]["listing_url"]=="https://www.ebay.com/itm/1234567890"


def test_unconfigured_feed_is_quiet_and_never_makes_up_prices():
    lookup=SoldgraphQuotes(client=SoldgraphClient(key=""),
                           monitor={"schema":1,"attempts":{},"last_provider_error":None,"requests_total":0})
    lookup.prime([{"name":NAME,"breakoutScore":90,"sleeperScore":90,"hypePct":1}],DAY)
    assert lookup.client.searches_used==0
    assert lookup.lookup(NAME,CARD,DAY) is None
    assert "missing" in lookup.monitor["last_provider_error"]


def test_repricing_holdings_uses_one_sold_search_only():
    client=FakeClient()
    lookup=SoldgraphQuotes(client=client,monitor={"schema":1,"attempts":{},
                              "last_provider_error":None,"requests_total":0})
    position={"player":NAME,"card":CARD,"variant_key":card_signature(TITLE,NAME,CARD),
              "last_mark_date":(DAY-timedelta(days=7)).isoformat()}
    lookup.prime([],DAY,positions=[position])
    assert client.kinds==["sold"]
    assert lookup.lookup(NAME,CARD,DAY)["median_cents"]==2900


def test_second_manual_run_same_day_does_not_use_more_trial_requests():
    client=FakeClient()
    monitor={"schema":1,"attempts":{},"last_provider_error":None,"requests_total":0}
    row={"name":NAME,"breakoutScore":90,"sleeperScore":90,"hypePct":1}
    first=SoldgraphQuotes(client=client,monitor=monitor)
    first.prime([row],DAY)
    assert client.kinds == ["sold","listings"]
    second=SoldgraphQuotes(client=client,monitor=monitor)
    second.prime([row],DAY)
    assert client.kinds == ["sold","listings"]
    assert second.lookup(NAME,CARD,DAY) is not None
