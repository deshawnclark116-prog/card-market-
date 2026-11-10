"""Public-recognition NEGATIVE screen for a raw-data-first MiLB detector.

Raw stats alone discover players. A public Top-100 ranking is ONLY evidence
that the player is already widely publicized: it can veto a 'pre-hype' label
but never nominate anyone. Absence from rankings does NOT prove low hobby hype.

Data: publicly visible MLB Pipeline Top-100 aggregation text. Anonymous GET,
no account or token. If unavailable, mark evidence UNKNOWN and never
misrepresent players as unranked.
"""
from __future__ import annotations

import html
import re
import unicodedata
import urllib.error
import urllib.request
from html.parser import HTMLParser

RANKING_URL = "https://prospectpulsev1.com/pipeline/"


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self._ignore=0

    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):
            self._ignore+=1
        if tag in ("a","p","div","li","span","td","tr"):
            self.parts.append(" ")

    def handle_endtag(self,tag):
        if tag in ("script","style"):
            self._ignore=max(0,self._ignore-1)
        if tag in ("a","p","div","li","span","td","tr"):
            self.parts.append(" ")

    def handle_data(self,data):
        if not self._ignore:
            self.parts.append(data)


def normalized(s):
    s=unicodedata.normalize("NFKD",str(s))
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+"," ",s.casefold()).strip()


def extract_ranked_text(markup):
    parser=_Text()
    parser.feed(markup)
    full=normalized(html.unescape(" ".join(parser.parts)))
    # If we cannot verify that this is a ranked Top-100 snapshot, fail
    # closed as UNKNOWN, not as evidence nobody has any hype.
    if "mlb pipeline top 100" not in full or "#1" not in full:
        return None
    begin=full.index("mlb pipeline top 100")
    end=full.find("ranked but omitted",begin)
    return full[begin:end if end!=-1 else None]


def public_top100_flags(names, loader=None):
    if loader is None:
        def loader():
            req=urllib.request.Request(
                RANKING_URL,headers={
                    "Accept":"text/html",
                    "User-Agent":"Mozilla/5.0 (compatible; CardMarketResearch/1.0)"})
            with urllib.request.urlopen(req,timeout=15) as response:
                return response.read(1_000_000).decode("utf-8","replace")
    try:
        content=loader()
        ranking_text=extract_ranked_text(content)
    except (urllib.error.URLError,TimeoutError,OSError,ValueError):
        ranking_text=None
    except Exception:
        ranking_text=None
    if ranking_text is None:
        return {n:None for n in names},False
    found={}
    for name in names:
        n=normalized(name)
        # Punctuation/space-bounded full name match only.
        found[name]=bool(re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])",
                                    ranking_text))
    return found,True
