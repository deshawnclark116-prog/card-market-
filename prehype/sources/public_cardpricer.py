"""Account-free, public CardPricer card sales for a conservative PAPER-only bot.

The documented anonymous GET API needs no key. NEVER trust its catalog price
or its provenance matcher alone: independently verify sale title year, exact
card number, set, player and grade to avoid false same-player comparisons.

No live buyable offer is claimed. Any paper entry is a synthetic execution
proxy based on an independently checked SOLD median plus friction.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone, timedelta
from statistics import median

BASE = "https://cardpricer.co"
MAX_DETAILS = 15
MAX_CATALOG_REQUESTS = 35
# Do NOT filter market discovery by the provider's unverified guide price.
# In practice a $250 first autograph has been assigned an $18 catalog mark.
MAX_REFERENCE_CARDS_PER_PLAYER = 5
MIN_SALES = 5
FRESH_DAYS = 14
WINDOW_DAYS = 30
NUMBERED = re.compile(r"(?:\b\d{1,3}\s*)?/\s*\d{1,3}\b")


def norm(value):
    raw = unicodedata.normalize("NFKD", str(value or ""))
    return re.sub(r"[^a-z0-9]+", " ",
                  "".join(c for c in raw if not unicodedata.combining(c)).lower()).strip()


def compact(value):
    return re.sub(r"[^a-z0-9]", "", norm(value))


def card_label(row):
    return f"{row['year']} {row['set']} #{row['cardNumber']} ({row['grade']})"


def reference_priority(row):
    """Card *identity* and collector relevance, without trusting a valuation."""
    series = norm(row.get("set"))
    if re.search(r"\b(autograph|autographs|autos|auto)\b", series):
        return 0
    if "bowman" in series and ("chrome" in series or "draft" in series):
        return 1
    if "rookie" in series or "topps chrome" in series:
        return 2
    return 3


def _date(raw):
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


def exact_sale_match(row, card):
    """Strict title identity; avoids catalog matches on just player+grade."""
    try:
        title = str(row["title"])
        player = str(card["player"])
        year = int(card["year"])
        series = str(card["set"])
        number = str(card["cardNumber"])
        grade = str(card["grade"])
    except (KeyError, ValueError, TypeError):
        return False

    if not player or not series or not number or not grade or not title:
        return False
    # "MINT 9" without PSA/BGS/SGC/CGC/TAG does not identify the grader.
    # It must never be pooled with a PSA 9 or called the same variant.
    if not re.match(r"^(PSA|BGS|SGC|CGC|TAG)\s+[0-9]+(?:\.[0-9]+)?$", grade, re.I):
        return False
    text = norm(title)
    pieces = text.split()
    if not all(re.search(r"\b" + re.escape(word) + r"\b", text)
               for word in norm(player).split()):
        return False
    if str(year) not in pieces:
        return False

    # Require explicit printed card number, never an incidental substring.
    number_pattern = r"(?:#|no\.?|card\s*#)\s*" + r"[-\s]*".join(re.escape(c) for c in compact(number)) + r"\b"
    if not re.search(number_pattern, title, flags=re.I):
        return False
    # Stop generic words masking a different set (e.g. Topps Chrome card
    # incorrectly matched to a Bowman Mega box by player/year/grade).
    set_tokens = [t for t in norm(series).split()
                  if t not in {"baseball", "cards", "card", "trading", "the", "of", "and", "edition"}]
    if not set_tokens or not all(re.search(r"\b" + re.escape(t) + r"\b", text)
                                 for t in set_tokens):
        return False
    if not all(re.search(r"\b" + re.escape(t) + r"\b", text)
               for t in norm(grade).split()):
        return False
    if row.get("grade") and norm(row["grade"]) != norm(grade):
        return False
    if NUMBERED.search(title) and not NUMBERED.search(str(card.get("set", ""))):
        # Do not confuse a numbered parallel with a plain base reference.
        return False
    variants = ("refractor", "xfractor", "superfractor", "sapphire", "mojo",
                "shimmer", "sepia", "prism", "foil", "wave", "parallel",
                "gold", "green", "blue", "red", "purple", "orange",
                "black", "pink", "negative", "variation", "short print")
    set_text = norm(series)
    for variant in variants:
        if re.search(r"\b" + re.escape(variant) + r"\b", text) and not re.search(
                r"\b" + re.escape(variant) + r"\b", set_text):
            return False
    if re.search(r"\b(reprint|replica|custom|lot|break|digital)\b", text):
        return False
    return True


def exact_sold_quote(card, provenance, day):
    """Only exact title-matched recent actual sales, never price estimates."""
    if not isinstance(provenance, dict):
        return None
    comp_data = provenance.get("comps") or {}
    entries = comp_data.get("recent") or []
    matches = []
    seen_urls = set()
    for item in entries:
        if not isinstance(item, dict) or not exact_sale_match(item, card):
            continue
        link = item.get("url")
        # Independent sales must have independently inspectable provenance.
        # Never inflate sample size through duplicate snapshots of one sale.
        if not isinstance(link, str) or not link.startswith("https://"):
            continue
        if link in seen_urls:
            continue
        seen_urls.add(link)
        try:
            price = float(item["price"])
        except (ValueError, TypeError, KeyError):
            continue
        sold_day = _date(item.get("soldDate"))
        if (not sold_day or not (day-timedelta(days=WINDOW_DAYS) <= sold_day <= day)
                or not (1 <= price <= 500) or price != price):
            continue
        # Sale URLs are provenance links, never proof of a current item for sale.
        matches.append((sold_day, int(round(price*100)), item.get("url")))
    if len(matches) < MIN_SALES:
        return None
    if (day-max(d for d, _, _ in matches)).days > FRESH_DAYS:
        return None
    earlier = [p for d, p, _ in matches if d < day-timedelta(days=14)]
    recent = [p for d, p, _ in matches if d >= day-timedelta(days=14)]
    if len(earlier) < 2 or len(recent) < 2:
        return None
    base = median(earlier)
    if base <= 0:
        return None
    return {
        "median_cents": int(round(median(p for _, p, _ in matches))),
        "comps": len(matches),
        "last_sale": max(d for d, _, _ in matches).isoformat(),
        "price_trend": round(median(recent)/base - 1, 4),
        "source": "cardpricer_public_exact_sold_proxy",
        "variant_key": str(card["id"]),
        "provenance_url": BASE + "/api/v1/cards/" + str(card["id"]) + "/provenance",
        "matched_sale_links": [u for _, _, u in matches[:5] if u],
        "entry_note": "No live listing available; reference median is NOT an executable offer",
    }


class CardPricerClient:
    """Anonymous, bounded GET requests against published public endpoints."""
    def __init__(self, opener=None):
        self.opener = opener or urllib.request.urlopen
        self.requests_used = 0
        self.errors = []
        self.max_requests = 52

    def get(self, path, params=None):
        if self.requests_used >= self.max_requests:
            self.errors.append("Public API daily request budget exhausted")
            return None
        if not path.startswith("/api/v1/") or ".." in path:
            raise ValueError("Non-public or unsafe API path")
        query = urllib.parse.urlencode(params or {})
        url = BASE + path + ("?" + query if query else "")
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "CardMarket-ResearchBot/1.0 (public anonymous API)",
        })
        self.requests_used += 1
        try:
            with self.opener(req, timeout=16) as resp:
                data = json.load(resp)
        except (urllib.error.URLError, ValueError, TimeoutError, OSError) as exc:
            self.errors.append(type(exc).__name__ + " while fetching public card data")
            return None
        if not isinstance(data, dict) or data.get("ok") is not True:
            self.errors.append("Public card API returned an invalid envelope")
            return None
        return data.get("data")

    def cards(self, player):
        return self.get("/api/v1/cards", {
            "sport":"baseball", "player":player, "limit":40,
            "sort":"volume",
        })

    def provenance(self, card_id):
        if not re.fullmatch(r"[a-f0-9-]{36}", str(card_id)):
            return None
        return self.get("/api/v1/cards/" + str(card_id) + "/provenance")


class PublicCardQuotes:
    """The GitHub runner can scan and price cards without a user account."""
    def __init__(self, client=None):
        self.client = client or CardPricerClient()
        self.today_quotes = {}
        self.checked = 0
        self.cards_found = 0
        self.exact_comps_found = 0
        self.checked_card = None

    def lookup(self, player, card, day):
        return self.today_quotes.get((player,card,day.isoformat()))

    peek = lookup

    def prime(self, candidates, day, positions=()):
        # Refresh each held card separately for its explicit persisted ID.
        for position in list(positions)[:5]:
            ref = position.get("variant_key")
            card = position.get("card")
            player = position.get("player")
            if not ref or not re.fullmatch(r"[a-f0-9-]{36}", str(ref)):
                continue
            detail=self.client.get("/api/v1/cards/"+ref)
            provenance=self.client.provenance(ref)
            if not isinstance(detail,dict):
                continue
            quote=exact_sold_quote(detail,provenance,day)
            if quote:
                self.today_quotes[(player,card,day.isoformat())]=quote

        available=[]
        # All 15 ranked players are displayed; public coverage will vary.
        for candidate in candidates[:MAX_CATALOG_REQUESTS]:
            player=candidate.get("name")
            candidate["cards"]={}
            if not isinstance(player,str) or not player:
                continue
            catalog=self.client.cards(player)
            self.checked += 1
            if not isinstance(catalog,list):
                continue
            eligible=[]
            for card in catalog:
                if not isinstance(card,dict) or norm(card.get("player"))!=norm(player):
                    continue
                if card.get("sport")!="baseball" or not card.get("id"):
                    continue
                if not all(card.get(field) for field in ("year","set","cardNumber","grade")):
                    continue
                try:
                    price = float(card.get("price") or 0)
                    sales = int(card.get("salesVolume30d") or 0)
                    label = card_label(card)
                except (ValueError,TypeError,KeyError):
                    continue
                if not (0 < price < 100000):
                    continue
                eligible.append((reference_priority(card), -sales, label, card, price, sales))
            # The public guide-price field cannot establish affordability.
            # Prefer autograph/Bowman identity even when the feed says $250+.
            eligible.sort(key=lambda row:(row[0],row[1],row[2]))
            for kind, _, label, card, price, sales in eligible[:MAX_REFERENCE_CARDS_PER_PLAYER]:
                self.cards_found += 1
                candidate["cards"][label]={
                    "price": price,  # RAW UNTRUSTED FEED, NOT A MARKET PRICE
                    "comps": sales,  # vendor count, not independently verified
                    "source":"CardPricer catalog — UNVERIFIED identifier/mark",
                    "card_id":card["id"],
                    "grade":card["grade"],
                    "card_priority":kind,
                    "price_validated":False,
                    # Catalog identity alone does NOT prove that a particular
                    # card is a factory-issued Bowman *1st* autographed variant.
                    # Post-purchase signatures, non-1st autos, and parallel
                    # mismatches must never pass this gate on text alone.
                    "manufacturer_first_bowman_auto_verified":False,
                }
                available.append((kind,
                                  -float(candidate.get("breakoutScore") or 0),
                                  -sales, player,label,card,candidate))
        available.sort(key=lambda x:(x[0],x[1],x[2],x[3],x[4]))
        for _,__,___,player,label,card,candidate in available[:MAX_DETAILS]:
            self.checked_card={"player":player,"card":label}
            provenance=self.client.provenance(card["id"])
            quote=exact_sold_quote(card,provenance,day)
            if quote is None:
                continue
            self.exact_comps_found += 1
            self.today_quotes[(player,label,day.isoformat())]=quote
            candidate["cards"][label]["verified_comps"]=quote["comps"]
            candidate["cards"][label]["verified_median_usd"]=quote["median_cents"]/100
        return {
            "provider":"CardPricer anonymous public API (NO KEY)",
            "no_accounts":True,
            "requests_used":self.client.requests_used,
            "players_checked":self.checked,
            "catalog_card_rows":self.cards_found,
            "catalog_price_field_trusted":False,
            "feed_price_filter_used":False,
            "card_variants_with_independent_five_sale_match":self.exact_comps_found,
            "last_error":self.client.errors[-1] if self.client.errors else None,
            "caution": "Public catalog marks may be incorrectly attributed; only independently exact-matched SOLD records can trigger a PAPER proxy buy.",
        }
