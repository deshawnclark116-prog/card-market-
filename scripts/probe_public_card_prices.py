"""Probe documented anonymous pricing endpoints from a real GitHub runner.

Diagnostics only; does not modify the paper ledger or persist external data.
No credentials, no scraping private/login pages, and no purchase logic.
"""
from __future__ import annotations
import json
import urllib.error
import urllib.parse
import urllib.request


BASE = "https://cardpricer.co"
ENDPOINTS = [
    "/api/v1/status",
    "/api/v1/cards?" + urllib.parse.urlencode({"sport": "baseball", "player": "coby mayo", "limit": 3}),
    "/api/v1/cards?" + urllib.parse.urlencode({"sport": "baseball", "limit": 3, "sort": "volume"}),
    "/api/v1/sales?" + urllib.parse.urlencode({"sport": "baseball", "limit": 3}),
    "/api/v1/sales?" + urllib.parse.urlencode({"sport": "baseball", "include": "listing", "limit": 3}),
]


def inspect(path: str):
    url = BASE + path
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "PreHype-Research/1.0 (public API validation)",
    })
    try:
        with urllib.request.urlopen(req, timeout=18) as resp:
            raw = resp.read(100_000)
            payload = json.loads(raw)
            print("SOURCE", path, "HTTP", resp.status, "bytes", len(raw))
            if not isinstance(payload, dict):
                print("UNEXPECTED", type(payload).__name__)
                return
            print("ROOT_KEYS", sorted(payload.keys()))
            print("META", json.dumps(payload.get("meta", {}), default=str)[:600])
            data = payload.get("data")
            if isinstance(data, list):
                print("ROWS", len(data))
                for row in data[:2]:
                    print("ROW", json.dumps(row, ensure_ascii=False, default=str)[:2100])
            else:
                print("BODY", json.dumps(payload, ensure_ascii=False, default=str)[:2700])
    except Exception as e:
        print("SOURCE", path, "ERROR", type(e).__name__, str(e)[:230])




def coverage():
    """Get genuine live names, matching card detail and provenance fields."""
    names = ["Walbert Urena", "Curtis Mead", "Logan Henderson", "Kyle Karros",
             "Coby Mayo", "Dalton Rushing", "Brady House", "Roman Anthony"]
    for player in names:
        params=urllib.parse.urlencode({"sport":"baseball","player":player,"limit":40})
        path="/api/v1/cards?"+params
        req=urllib.request.Request(BASE+path,headers={"Accept":"application/json","User-Agent":"PreHype/1.0"})
        try:
            with urllib.request.urlopen(req,timeout=18) as resp:
                p=json.load(resp)
            data=p.get("data") or []
            good=[d for d in data if str(d.get("player","")).casefold()==player.casefold()
                  and (d.get("price") or 0) <= 35]
            print("COVERAGE",player,"total",p.get("meta",{}).get("pagination",{}).get("total"),
                  "priced_<=35",len(good))
            for row in good[:2]:
                print("MATCH",json.dumps(row,ensure_ascii=False)[:950])
        except Exception as e:
            print("COVERAGE_ERROR",player,type(e).__name__,str(e)[:150])
    for id in ("d2b4882a-b696-4b72-a908-f4a91bfd0d51",
               "47345c71-1ea9-422a-816e-ba6d68d697c0"):
        inspect("/api/v1/cards/"+id+"/provenance")
        inspect("/api/v1/cards/"+id)

if __name__ == "__main__":
    coverage()
