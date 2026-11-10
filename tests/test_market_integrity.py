"""Regression checks for real-world bad prices and misleading search hype."""
from datetime import date
from prehype.paper_bot import make_ledger, market_data_ready, simulate_day
from prehype.scouting_report import build_scouting_report, to_markdown
from prehype.sources.public_cardpricer import PublicCardQuotes

DAY=date(2026,11,10)

def no_quote(*args):
    return None

def strong_quote(*args):
    return {"median_cents":1800,"comps":8,"last_sale":DAY.isoformat(),
            "price_trend":0.0}

def candidate(name,breakout,source_price=None):
    cards={} if source_price is None else {
        "2024 Bowman Draft Chrome Prospect Autographs #CPAJC (MINT 9)":{
            "price":source_price, "source":"UNVERIFIED catalog mark"
        }
    }
    return {"name":name, "breakoutScore":breakout,"dealScore":None,
            "cardHypeVerified":False,"hypePct":None,
            "searchInterestVsJudgePct":4.0,"priceTrend":None,"cards":cards,
            "reason":"xwOBA improved"}


def test_feed_claim_of_18_dollars_never_printed_as_market_price():
    rows=[candidate("Jac Caglianone",81,18.02)]
    data=build_scouting_report(rows,no_quote,DAY,make_ledger(DAY),"WAITING")
    md=to_markdown(data)
    assert "USD 18.02" not in md
    assert "UNVERIFIED — HIDDEN" in md
    assert data["players"][0]["checks"][0]["catalog_raw_untrusted_usd"]==18.02
    assert data["players"][0]["checks"][0]["catalog_guide_price_usd"] is None
    assert data["players"][0]["checks"][0]["sold_median_usd"] is None
    assert "NOT VERIFIED BUY" in md


def test_google_trends_vs_aaron_judge_is_not_card_hype():
    rows=[candidate("Jac Caglianone",81,18.02)]
    md=to_markdown(build_scouting_report(rows,no_quote,DAY,
                                        make_ledger(DAY),"WAITING"))
    assert "4.0% of Judge" in md
    assert "NOT MEASURED" in md
    assert "4.0% hype" not in md


def test_unknown_prices_sort_by_skill_not_alphabetical():
    data=build_scouting_report([candidate("Zed",83),
                                candidate("Aaron",19)],
                               no_quote,DAY,make_ledger(DAY),"WAITING")
    assert [r["name"] for r in data["players"]]==["Zed","Aaron"]


def test_cannot_start_month_or_buy_with_unverified_collector_hype():
    c=candidate("Jac Caglianone",89,18.02)
    c["dealScore"]=90
    c["priceTrend"]=0.01
    # Even fabricated good comps cannot make unknown hobby attention into quiet.
    assert not market_data_ready([c],strong_quote,DAY)
    state=make_ledger(DAY)
    result=simulate_day(state,[c],strong_quote,DAY)
    assert result["buys"]==[]
    assert state["cash_cents"]==10000


class FakeCardPricer:
    def __init__(self):
        self.requests_used=0
        self.errors=[]
    def cards(self,player):
        self.requests_used+=1
        return [
            {"id":"11111111-1111-1111-1111-111111111111",
             "player":player,"sport":"baseball","year":2024,
             "set":"Bowman Draft Chrome Prospect Autographs","cardNumber":"CPAJC",
             "grade":"MINT 9","price":18.02,"salesVolume30d":0},
            {"id":"22222222-2222-2222-2222-222222222222",
             "player":player,"sport":"baseball","year":2024,
             "set":"Bowman Draft Chrome Prospect Autographs","cardNumber":"CPA-JC",
             "grade":"PSA 9","price":270.0,"salesVolume30d":0}
        ]
    def provenance(self,card_id):
        self.requests_used+=1
        return {"comps":{"recent":[]}}


def test_premium_cards_not_hidden_by_22_dollar_feed_price_cutoff():
    c=candidate("Jac Caglianone",81)
    q=PublicCardQuotes(client=FakeCardPricer())
    diag=q.prime([c],DAY)
    assert len(c["cards"])==2
    assert any(v["price"]>200 for v in c["cards"].values())
    assert diag["feed_price_filter_used"] is False
    assert diag["card_variants_with_independent_five_sale_match"]==0
    data=build_scouting_report([c],q,DAY,make_ledger(DAY),"WAITING")
    assert "USD 270.00" not in to_markdown(data)
