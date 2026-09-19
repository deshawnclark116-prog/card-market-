"""A tiny JSON API so a web frontend can show the sleeper board.

    python -m prehype serve            # http://localhost:8000/api/sleepers

Endpoints:
    GET /                       health/help
    GET /api/sleepers           run the scan, return the ranked list as JSON
    GET /api/sleepers?demo=1    canned sample data (instant, no network) —
                                point your frontend here while building the UI

Query params for the live endpoint:
    type=both|batter|pitcher   (default both)
    top=15                      how many to return
    prices=1|0                  include the eBay price step (default 1)
    hype=1|0                    include the Google Trends hype step (default 1)
    year=2026                   season (default current)

Uses only the standard library (http.server). Results are cached in memory for
a while so repeated requests don't re-run the whole scan. eBay price data needs
to run from a non-blocked (home/residential) IP or with an eBay API token; when
it can't, prices come back null and the rest of the board still works.
"""

from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from prehype.breakouts import add_hype, add_prices, find_breakouts_multi

# ---- serialization --------------------------------------------------------- #


def _price_status(trend: float | None) -> str:
    if trend is None:
        return "unknown"
    if trend <= 0.05:
        return "still cheap"
    if trend >= 0.30:
        return "LATE"
    return "window closing"


def serialize_hit(h) -> dict:
    """Turn a BreakoutHit into the JSON shape the frontend expects."""

    cards = {
        label: {
            "price": (round(median) if median is not None else None),
            "comps": count,
        }
        for label, (median, count) in h.card_prices.items()
    }
    return {
        "name": h.batter.name,
        "position": h.pos,
        "age": h.age,
        "dealScore": round(h.deal_score) if h.deal_score is not None else None,
        "breakoutScore": round(h.score),
        "sleeperScore": round(h.sleeper_score) if h.sleeper_score is not None else None,
        "hypePct": round(h.interest) if h.interest is not None else None,
        "kind": h.kind,
        "reason": h.reason,
        "priceTrend": round(h.price_trend, 3) if h.price_trend is not None else None,
        "priceStatus": _price_status(h.price_trend),
        "cards": cards,
    }


# ---- the scan (with a simple in-memory cache) ------------------------------ #

_CACHE: dict[tuple, tuple[float, list[dict]]] = {}
_TTL = 3600.0  # seconds


def run_scan(
    *,
    scan_type: str = "both",
    top: int = 15,
    prices: bool = True,
    hype: bool = True,
    year: int | None = None,
    use_cache: bool = True,
) -> list[dict]:
    """Run the full pipeline and return serialized results."""

    key = (scan_type, top, prices, hype, year)
    if use_cache and key in _CACHE:
        ts, data = _CACHE[key]
        if time.time() - ts < _TTL:
            return data

    types = {
        "both": ("batter", "pitcher"),
        "batter": ("batter",),
        "pitcher": ("pitcher",),
    }.get(scan_type, ("batter", "pitcher"))

    hits = find_breakouts_multi(year=year, top=top, types=types)
    if hype:
        hits = add_hype(hits)
    hits = hits[:top]
    if prices:
        hits = add_prices(hits)

    data = [serialize_hit(h) for h in hits]
    _CACHE[key] = (time.time(), data)
    return data


# ---- canned demo data (instant, no network) -------------------------------- #

DEMO_DATA: list[dict] = [
    {
        "name": "Kyle Karros", "position": "BAT", "age": 24,
        "dealScore": 58, "breakoutScore": 64, "sleeperScore": 61, "hypePct": 2,
        "kind": "leveling up",
        "reason": "xwOBA jumped .258 -> .340 (+.082) vs last year — leveled up while still under the radar",
        "priceTrend": 0.04, "priceStatus": "still cheap",
        "cards": {"Bowman 1st auto": {"price": 45, "comps": 12}, "Rookie auto": {"price": 28, "comps": 7}},
    },
    {
        "name": "Curtis Mead", "position": "BAT", "age": 25,
        "dealScore": 49, "breakoutScore": 72, "sleeperScore": 51, "hypePct": 12,
        "kind": "leveling up",
        "reason": "xwOBA jumped .291 -> .358 (+.067) vs last year — leveled up while still under the radar",
        "priceTrend": 0.09, "priceStatus": "still cheap",
        "cards": {"Bowman 1st auto": {"price": 60, "comps": 9}, "Rookie auto": {"price": 34, "comps": 5}},
    },
    {
        "name": "Payton Tolle", "position": "PIT", "age": 23,
        "dealScore": 12, "breakoutScore": 88, "sleeperScore": 51, "hypePct": 17,
        "kind": "emerging",
        "reason": "new arm — already tough to hit (xwOBA-against .253, lower is better)",
        "priceTrend": 0.62, "priceStatus": "LATE",
        "cards": {"Bowman 1st auto": {"price": 210, "comps": 20}, "Rookie auto": {"price": None, "comps": 0}},
    },
]


# ---- HTTP handler ---------------------------------------------------------- #


class _Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status: int = 200) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # CORS preflight
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)

        def flag(name: str, default: bool) -> bool:
            if name not in q:
                return default
            return q[name][0].lower() not in ("0", "false", "no")

        if parsed.path in ("/", "/health"):
            self._send_json({
                "ok": True,
                "endpoints": ["/api/sleepers", "/api/sleepers?demo=1"],
            })
            return

        if parsed.path == "/api/sleepers":
            if flag("demo", False):
                self._send_json(DEMO_DATA)
                return
            try:
                data = run_scan(
                    scan_type=q.get("type", ["both"])[0],
                    top=int(q.get("top", ["15"])[0]),
                    prices=flag("prices", True),
                    hype=flag("hype", True),
                    year=int(q["year"][0]) if "year" in q else None,
                )
                self._send_json(data)
            except Exception as e:  # keep the server alive; report the error
                self._send_json({"error": str(e)}, status=500)
            return

        self._send_json({"error": "not found"}, status=404)

    def log_message(self, *args) -> None:  # quieter console
        return


def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), _Handler)
    print(f"prehype API on http://localhost:{port}")
    print(f"  try: http://localhost:{port}/api/sleepers?demo=1   (instant sample data)")
    print(f"       http://localhost:{port}/api/sleepers          (live scan — slower)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.shutdown()
