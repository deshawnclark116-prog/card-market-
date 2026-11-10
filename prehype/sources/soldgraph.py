"""Soldgraph sold+active eBay search for conservative sports-card PAPER decisions.

A vendor API key is required. Never invent sold prices, buy listings, shipping
or variant identities; no credential or real purchasing flow is implemented.

The free allowance is one-time, so only ONE new card-reference pair (two
searches: sold + active) is fetched per daily run. Cached reports are persisted
between short-lived GitHub Actions runners, including failed/no-result checks.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from statistics import median

BASE_URL = "https://api.soldgraph.com"
MONITOR_PATH = "data/card_bot_market_monitor.json"
MAX_NEW_SEARCHES = 2
DISALLOW = re.compile(
    r"\b(reprint|replica|custom|digital|break|lot|bundle|non[\s-]?auto|unsigned|"
    r"psa|bgs|sgc|cgc|graded|slab|gem[\s-]?mt|redemption|sealed pack|"
    r"printing plate|proof|oversized)\b", re.I,
)
COLOURS = ("sapphire", "refractor", "purple", "orange", "green", "yellow",
           "black", "blue", "gold", "red", "mojo", "shimmer", "wave", "sparkle")
EXCLUDE_SERIAL = re.compile(r"(?:\b\d{1,3}\s*)?/\s*\d{1,3}\b")
YEARS = re.compile(r"\b20(?:0[0-9]|1[0-9]|2[0-9]|3[0-9])\b")
NUMBER = re.compile(r"(?:#\s*|\b)((?:bca|cpa|bcp|cda|bcpa|pa|ra|rda)[- ]?[a-z0-9]{1,8})\b", re.I)


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    return unicodedata.normalize("NFKC", "".join(
        c for c in value if not unicodedata.combining(c))).lower()


def card_signature(title: str, player: str, card: str) -> str | None:
    """Require name, named set and explicit year + card number + raw auto.

    Reject numbered parallels, slabs, non-autos, breaks, lots, ambiguous titles.
    Signatures are deliberately strict to avoid fake comparable sales.
    """
    text = norm(title)
    name = norm(player)
    if not name or any(not re.search(r"\b" + re.escape(part) + r"\b", text)
                       for part in name.split()):
        return None
    if DISALLOW.search(text) or EXCLUDE_SERIAL.search(text):
        return None
    if not re.search(r"\b(auto|autograph|autographed|signed)\b", text):
        return None
    if card == "Bowman 1st auto":
        if not all(re.search(r"\b" + word + r"\b", text)
                   for word in ("bowman", "chrome")):
            return None
        if not re.search(r"\b(1st|first)\b", text):
            return None
        set_name = "bowman-chrome-1st"
    elif card == "Rookie auto":
        if not re.search(r"\b(rc|rookie)\b", text):
            return None
        if re.search(r"\btopps\b", text) and re.search(r"\bchrome\b", text):
            set_name = "topps-chrome-rookie"
        elif re.search(r"\bpanini\b", text) and re.search(r"\bprizm\b", text):
            set_name = "panini-prizm-rookie"
        else:
            return None
    else:
        return None
    years = YEARS.findall(text)
    numbers = NUMBER.findall(text)
    if len(set(years)) != 1 or not numbers:
        return None
    # This pilot considers only non-parallel base autos; never group colours or
    # numbered variations with the plain base card.
    if any(re.search(r"\b" + colour + r"\b", text) for colour in COLOURS):
        return None
    return "|".join((years[0], set_name, numbers[0].replace(" ", "").replace("-", "")))


def listing_amount(row: dict, field="displayed_price") -> int | None:
    price = row.get(field)
    if not isinstance(price, dict) or price.get("currency") != "USD":
        return None
    try:
        amount = float(price["amount"])
    except (TypeError, ValueError, KeyError):
        return None
    if not 0 <= amount < 1_000_000 or amount != amount:
        return None
    return int(round(amount * 100))


def safe_ebay_listing_url(value) -> bool:
    if not isinstance(value, str):
        return False
    p = urllib.parse.urlparse(value)
    return (p.scheme == "https" and p.hostname in ("www.ebay.com", "ebay.com")
            and p.path.startswith("/itm/") and not p.username and not p.password)


def compute_quote(sold_rows, listing_rows, player, card, day: date) -> dict | None:
    """Only matching, verified-price sold comps and actual fixed-price offers.

    Soldgraph's best-offer flag means the displayed sale price may be the
    original ASK, so exclude those rows from all price calculations.
    """
    sold_by_variant = {}
    cutoff = day - timedelta(days=45)
    for row in sold_rows:
        key = card_signature(row.get("title"), player, card)
        if not key or row.get("best_offer_accepted") or row.get("displayed_price_range"):
            continue
        price = listing_amount(row)
        try:
            sold_day = date.fromisoformat(str(row["sold_date"])[:10])
        except (KeyError, TypeError, ValueError):
            continue
        if price is None or price < 100 or sold_day < cutoff or sold_day > day:
            continue
        sold_by_variant.setdefault(key, []).append((sold_day, price))

    viable = {}
    for variant, sales in sold_by_variant.items():
        if len(sales) < 5:
            continue
        last_sale = max(d for d, _ in sales)
        if (day - last_sale).days > 14:
            continue
        early = [p for d, p in sales if d < day - timedelta(days=21)]
        recent = [p for d, p in sales if d >= day - timedelta(days=21)]
        if len(early) < 2 or len(recent) < 2:
            continue
        previous = median(early)
        if previous <= 0:
            continue
        trend = (median(recent) / previous) - 1
        viable[variant] = {
            "median_cents": int(round(median([p for _, p in sales]))),
            "price_trend": round(trend, 4),
            "comps": len(sales),
            "last_sale": last_sale.isoformat(),
        }

    offers = []
    for row in listing_rows:
        if row.get("format") != "fixed_price" or row.get("displayed_price_range"):
            continue
        url = row.get("link")
        if not safe_ebay_listing_url(url):
            continue
        variant = card_signature(row.get("title"), player, card)
        if variant not in viable:
            continue
        ask = listing_amount(row)
        shipping = listing_amount(row, "displayed_shipping")
        if ask is None or shipping is None or ask < 500:
            continue
        # Estimated 6% tax on item + shipping; not an exact destination quote.
        tax = int(round((ask + shipping) * 0.06))
        all_in = ask + shipping + tax
        med = viable[variant]["median_cents"]
        # Estimate eBay fees and outward shipping, never claim profit on an
        # entry priced above a plausible net resale.
        net_exit = max(0, int(round(med * .85)) - 350)
        if all_in > 2500 or net_exit - all_in < 200:
            continue
        offers.append((all_in, str(url), variant, row, ask, shipping, tax))

    if not offers:
        return None
    all_in, url, variant, row, ask, shipping, tax = min(offers)
    quote = {
        **viable[variant],
        "source": "soldgraph",
        "variant_key": variant,
        "listing_url": url,
        "listing_title": row.get("title"),
        "ask_cents": ask,
        "shipping_cents": shipping,
        "tax_estimate_cents": tax,
        "all_in_ask_cents": all_in,
        "net_resale_margin_cents": max(0, int(round(viable[variant]["median_cents"]*.85)) - 350) - all_in,
    }
    return quote


def compute_variant_mark(sold_rows, player, card, variant, day):
    """A new value estimate for a HELD exact reference-card variant."""
    prices=[]
    cutoff=day-timedelta(days=45)
    dates=[]
    for row in sold_rows:
        if (card_signature(row.get("title"),player,card) != variant
                or row.get("best_offer_accepted") or row.get("displayed_price_range")):
            continue
        try:
            sold_day=date.fromisoformat(str(row["sold_date"])[:10])
        except (KeyError,ValueError,TypeError):
            continue
        price=listing_amount(row)
        if price is None or price<=0 or sold_day<cutoff or sold_day>day:
            continue
        prices.append(price)
        dates.append(sold_day)
    if len(prices)<5 or (day-max(dates)).days>14:
        return None
    return {
        "median_cents":int(round(median(prices))),
        "comps":len(prices),
        "last_sale":max(dates).isoformat(),
        "source":"soldgraph_mark",
        "variant_key":variant,
    }


class SoldgraphClient:
    def __init__(self, key=None, opener=None, max_searches=MAX_NEW_SEARCHES):
        self.key = key if key is not None else os.environ.get("SOLDGRAPH_KEY", "")
        self.opener = opener or urllib.request.urlopen
        self.max_searches = max_searches
        self.searches_used = 0
        self.last_error = None

    def _request(self, path, *, params=None):
        if not self.key:
            self.last_error = "SOLDGRAPH_KEY is not configured"
            return None
        url = BASE_URL + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url, headers={"Authorization": "Bearer " + self.key,
                          "Accept": "application/json",
                          "User-Agent": "CardMarketPaperBot/1.0"})
        try:
            with self.opener(req, timeout=35) as resp:
                payload = json.load(resp)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            # Never include request credentials in public logs.
            self.last_error = "Market data API unavailable: " + type(exc).__name__
            return None
        for _ in range(5):
            status = payload.get("status")
            if status == "complete":
                result = payload.get("result") or {}
                if result.get("provider") == "ebay" and result.get("country") == "us":
                    return result.get("data", [])
                self.last_error = "Unexpected market data payload"
                return None
            if status == "failed":
                self.last_error = "Data job failed: " + str((payload.get("error") or {}).get("code","unknown"))
                return None
            poll_url = payload.get("poll_url")
            if status != "pending" or not isinstance(poll_url,str) or not re.fullmatch(r"/v1/jobs/[A-Za-z0-9-]+",poll_url):
                self.last_error = "Unexpected pending market job"
                return None
            req = urllib.request.Request(
                BASE_URL + poll_url + "?wait=20",
                headers={"Authorization": "Bearer " + self.key,
                         "Accept": "application/json"})
            try:
                with self.opener(req, timeout=35) as resp:
                    payload=json.load(resp)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                self.last_error = "Market job timeout: " + type(exc).__name__
                return None
        self.last_error = "Market job did not complete"
        return None

    def search(self, kind, query):
        if self.searches_used >= self.max_searches:
            self.last_error = "Daily market API request budget exhausted"
            return None
        if kind not in ("sold", "listings"):
            raise ValueError("unsupported market search")
        if not self.key:
            self.last_error = "SOLDGRAPH_KEY is not configured"
            return None
        self.searches_used += 1
        params = {"q": query, "country":"us", "count":"120",
                  "item_location":"domestic",
                  "sort": "recently_sold" if kind=="sold" else "price_asc"}
        if kind=="listings":
            params["buying_format"]="buy_it_now"
        return self._request("/v1/ebay/" + kind, params=params)


def load_monitor(path=MONITOR_PATH):
    try:
        data=json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema") == 1:
            return data
    except (OSError, ValueError):
        pass
    return {"schema":1,"attempts":{}, "last_provider_error":None, "requests_total":0}


def save_monitor(state, path=MONITOR_PATH):
    target=Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n", encoding="utf-8")


class SoldgraphQuotes:
    """Throttled, observable quote lookup with no network on dashboard reads."""
    def __init__(self, client=None, monitor=None):
        self.client=client or SoldgraphClient()
        self.monitor=monitor if monitor is not None else load_monitor()
        self.today_quotes={}
        self.checked_card=None

    def lookup(self, player, card, day):
        return self.today_quotes.get((player,card,day.isoformat()))

    peek = lookup

    def prime(self, candidates, day, positions=()):
        if not self.client.key:
            self.monitor["last_provider_error"]="SOLDGRAPH_KEY missing — no pricing requests made"
            return
        # Manual reruns on the same calendar day must NOT spend another pair
        # of one-time trial credits. Reload the already checked quote instead.
        today_label = day.isoformat()
        previous_today = [
            (key, value) for key, value in self.monitor["attempts"].items()
            if value.get("checked_on") == today_label
        ]
        if previous_today:
            for key, value in previous_today:
                parts = key.split("|")
                if parts[0] == "MARK" and len(parts) == 3:
                    player, card = parts[1], parts[2]
                elif len(parts) == 2:
                    player, card = parts
                else:
                    continue
                self.today_quotes[(player, card, today_label)] = value.get("quote")
                self.checked_card = {"player": player, "card": card}
            return
        # With a small free quota, refresh each held card about weekly,
        # preserving the card's exact matched variant identity.
        due=[]
        for position in positions:
            last=position.get("last_mark_date")
            if not position.get("variant_key"):
                continue
            try:
                age=(day-date.fromisoformat(last)).days
            except (ValueError,TypeError):
                age=99
            key="MARK|"+position["player"]+"|"+position["card"]
            checked=self.monitor["attempts"].get(key,{}).get("checked_on")
            try:
                recently_tried=(day-date.fromisoformat(checked)).days<3
            except (ValueError,TypeError):
                recently_tried=False
            if age>=5 and not recently_tried:
                due.append((-age,position,key))
        if due:
            due.sort(key=lambda pair: pair[0])
            _,position,key=due[0]
            player=position["player"]
            card=position["card"]
            query=(player+" bowman chrome 1st auto" if card=="Bowman 1st auto"
                   else player+" rookie auto")
            sold=self.client.search("sold",query)
            mark=compute_variant_mark(sold or [],player,card,
                                      position["variant_key"],day) if sold is not None else None
            self.today_quotes[(player,card,day.isoformat())]=mark
            self.checked_card={"player":player,"card":card}
            self.monitor["attempts"][key]={
                "checked_on":day.isoformat(),"mark_refresh":True,
                "sold_rows":len(sold or []),"quote":mark,
            }
            self.monitor["requests_total"] += self.client.searches_used
            self.monitor["last_provider_error"]=self.client.last_error
            return
        # Examine the strongest qualified-not-held reference we have not just
        # examined in the past week. Rotate instead of wasting 100 free credits
        # on the same top player every morning.
        options=[]
        for c in candidates:
            try:
                name=c["name"]
                score=float(c.get("sleeperScore") or c.get("breakoutScore") or 0)
                hype=c.get("hypePct")
                if float(c["breakoutScore"]) < 45 or hype is None or float(hype)>30:
                    continue
            except (KeyError,TypeError,ValueError):
                continue
            for card in ("Bowman 1st auto","Rookie auto"):
                key=name+"|"+card
                item=self.monitor["attempts"].get(key,{})
                last=item.get("checked_on")
                if last == day.isoformat():
                    # A manual second run today must not reconsume credits.
                    if item.get("quote"):
                        self.today_quotes[(name,card,day.isoformat())]=item["quote"]
                    continue
                try:
                    old = date.fromisoformat(last)
                    if (day-old).days < 7:
                        continue
                except (TypeError,ValueError):
                    pass
                options.append((-score,name,card,key))
        if not options:
            self.monitor["last_provider_error"]="No fresh unexamined player-card pairs"
            return
        options.sort()
        # Choose the best candidate but disfavor repeatedly failing queries by
        # selecting the oldest last-checked query among the current top 5.
        shortlist=options[:5]
        shortlist.sort(key=lambda o:(self.monitor["attempts"].get(o[3],{}).get("checked_on",""),o[0],o[1],o[2]))
        _,player,card,key=shortlist[0]
        self.checked_card={"player":player,"card":card}
        query=(player+" bowman chrome 1st auto" if card=="Bowman 1st auto"
               else player+" rookie auto")
        sold=self.client.search("sold",query)
        active=self.client.search("listings",query) if sold is not None else None
        quote=compute_quote(sold,active,player,card,day) if sold is not None and active is not None else None
        self.today_quotes[(player,card,day.isoformat())]=quote
        self.monitor["attempts"][key]={
            "checked_on":day.isoformat(),
            "sold_feed_returned":sold is not None,
            "active_feed_returned":active is not None,
            "sold_rows":len(sold or []),
            "active_rows":len(active or []),
            "qualified_offer":bool(quote),
            "quote":quote,
        }
        self.monitor["requests_total"] += self.client.searches_used
        self.monitor["last_provider_error"]=self.client.last_error
