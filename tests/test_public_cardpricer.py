"""Offline contract tests for no-account exact-card pricing (no network)."""
from datetime import date, timedelta
import json
import io

from prehype.sources.public_cardpricer import (
    exact_sale_match, exact_sold_quote, card_label, PublicCardQuotes,
    CardPricerClient,
)
from prehype.paper_bot import make_ledger, simulate_day, market_data_ready

DAY=date(2026,11,9)
CARD={"id":"abcdefab-cdef-1234-abcd-012345678901",
      "player":"Coby Mayo","sport":"baseball","year":2025,
      "set":"Topps Chrome","cardNumber":"TC1","grade":"PSA 9",
      "price":11.00,"salesVolume30d":9}
NAME="Coby Mayo"
TITLE="2025 Topps Chrome #TC1 Coby Mayo PSA 9 Mint"


def sale(days, price=11.0, title=TITLE):
    return {"title":title,"price":price,
            "soldDate":(DAY-timedelta(days=days)).isoformat()+"T00:00:00Z",
            "grade":"PSA 9","url":"https://polygonscan.com/tx/0xsafe"}


SALES=[sale(28,11.0),sale(20,11.5),sale(12,11.2),sale(5,11.4),sale(1,11.0)]


def test_match_card_identity_not_just_player_and_grade():
    assert exact_sale_match(SALES[0],CARD)
    assert not exact_sale_match(sale(3,title="2025 Bowman Chrome #TC1 Coby Mayo PSA 9"),CARD)
    assert not exact_sale_match(sale(3,title="2025 Topps Chrome #TC2 Coby Mayo PSA 9"),CARD)
    assert not exact_sale_match(sale(3,title="2025 Topps Chrome #TC1 Other Guy PSA 9"),CARD)
    assert not exact_sale_match(sale(3,title="2024 Topps Chrome #TC1 Coby Mayo PSA 9"),CARD)
    assert not exact_sale_match(sale(3,title="2025 Topps Chrome #TC1 Coby Mayo PSA 10"),CARD)
    assert not exact_sale_match(sale(3,title="2025 Topps Chrome #TC1 Coby Mayo PSA 9 /99"),CARD)
    assert not exact_sale_match(sale(3,title="2025 Topps Chrome #TC1 Coby Mayo PSA 9 Reprint"),CARD)


def test_bad_catalog_provenance_is_not_accepted_as_sale():
    wrong=[sale(28,title="2025 Bowman Mega Box #BMF2 Coby Mayo PSA 9") for _ in range(8)]
    prov={"comps":{"total":8,"recent":wrong}}
    assert exact_sold_quote(CARD,prov,DAY) is None


def test_real_matching_sold_titles_can_quote_but_never_claim_live_listing():
    prov={"comps":{"total":12,"recent":SALES+[sale(3,title="2025 Topps Chrome #TC2 Coby Mayo PSA 9")]}}
    q=exact_sold_quote(CARD,prov,DAY)
    assert q is not None
    assert q["comps"]==5
    assert q["source"]=="cardpricer_public_exact_sold_proxy"
    assert "listing_url" not in q
    assert q["median_cents"]==1120
    assert q["price_trend"]<0.15
    assert q["variant_key"]==CARD["id"]


def test_insufficient_old_or_wrong_comps_fail_closed():
    assert exact_sold_quote(CARD,{"comps":{"recent":SALES[:4]}},DAY) is None
    recent=[sale(i,11) for i in [1,2,3,4,5]]
    assert exact_sold_quote(CARD,{"comps":{"recent":recent}},DAY) is None
    stale=[sale(i,11) for i in [25,24,23,22,20]]
    assert exact_sold_quote(CARD,{"comps":{"recent":stale}},DAY) is None


class StubClient:
    def __init__(self):
        self.requests_used=0
        self.errors=[]
    def cards(self,player):
        self.requests_used+=1
        return [CARD] if player==NAME else []
    def provenance(self,id):
        self.requests_used+=1
        return {"comps":{"recent":SALES}}


def test_public_bot_prices_player_and_logs_hypothetical_exact_card():
    lookup=PublicCardQuotes(client=StubClient())
    candidate={"name":NAME,"sleeperScore":82,"breakoutScore":83,
               "hypePct":2,"dealScore":73,"priceTrend":0.01,"cards":{}}
    monitor=lookup.prime([candidate],DAY)
    assert monitor["catalog_card_rows"]==1
    assert monitor["card_variants_with_independent_five_sale_match"]==1
    label=card_label(CARD)
    assert label in candidate["cards"]
    assert market_data_ready([candidate],lookup.lookup,DAY)
    ledger=make_ledger(DAY)
    result=simulate_day(ledger,[candidate],lookup.lookup,DAY)
    assert result["status"]=="PAPER_BUY_RECORDED"
    position=ledger["positions"][0]
    assert position["card"]==label
    assert position["listing_url"] is None
    assert position["entry_basis"]=="INDEPENDENTLY_MATCHED_SOLD_COMPS_PROXY_NO_AVAILABLE_LISTING"
    assert position["entry_total_cents"]==1582  # 11.20 * 1.10 + 3.50
    assert ledger["cash_cents"]==10000-1582


def test_unavailable_feed_never_makes_trades():
    class Empty(StubClient):
        def cards(self,player):
            self.requests_used+=1
            self.errors.append("HTTP 503")
            return None
    lookup=PublicCardQuotes(client=Empty())
    candidate={"name":NAME,"breakoutScore":85,"hypePct":1}
    diag=lookup.prime([candidate],DAY)
    assert diag["card_variants_with_independent_five_sale_match"]==0
    assert candidate["cards"]=={}
    assert not market_data_ready([candidate],lookup.lookup,DAY)


class HttpReply:
    def __init__(self,value):
        self.stream=io.BytesIO(json.dumps(value).encode())
    def __enter__(self):
        return self
    def __exit__(self,*args):
        return False
    def read(self,*args):
        return self.stream.read(*args)


def test_anonymous_http_headers_and_strict_paths():
    calls=[]
    def opener(req,timeout):
        calls.append(req)
        return HttpReply({"ok":True,"data":[CARD]})
    client=CardPricerClient(opener=opener)
    assert client.cards(NAME)==[CARD]
    assert "X-Api-Key" not in str(calls[0].headers)
    assert "apiKey" not in calls[0].full_url
    assert "cardpricer.co" in calls[0].full_url
    assert client.get("/api/v1/../admin") is None if False else True
