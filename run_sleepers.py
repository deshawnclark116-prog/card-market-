#!/usr/bin/env python3
"""One command to get the full sleeper list on your own computer.

    python run_sleepers.py

It does all three steps:
  1. Find hitters who are quietly getting good   (Baseball Savant)
  2. Drop the ones people already hype            (Google Trends)
  3. Check what their cards actually cost         (eBay sold comps)

eBay only works from a normal home internet connection (it blocks data-center
servers), so run this on your laptop/desktop, not a cloud box.
"""

from __future__ import annotations

import argparse

from prehype.breakouts import add_hype, add_prices, find_breakouts_multi


def main() -> int:
    ap = argparse.ArgumentParser(description="Find cheap, quiet, breaking-out MLB cards.")
    ap.add_argument("--year", type=int, default=None, help="season year (default: this year)")
    ap.add_argument("--min-pa", type=int, default=250, help="min plate appearances (hitters)")
    ap.add_argument("--min-pa-pitcher", type=int, default=200, help="min batters faced (pitchers)")
    ap.add_argument(
        "--type", choices=["both", "batter", "pitcher"], default="both",
        help="scan hitters, pitchers, or both (default: both)",
    )
    ap.add_argument("--top", type=int, default=10, help="how many players to show")
    ap.add_argument("--no-prices", action="store_true", help="skip the eBay price step")
    ap.add_argument("--include-relievers", action="store_true", help="keep relievers (default: starters only)")
    ap.add_argument("--anchor", default="Aaron Judge", help="famous player for the hype meter")
    args = ap.parse_args()

    types = {"both": ("batter", "pitcher"), "batter": ("batter",), "pitcher": ("pitcher",)}[args.type]
    print("\nStep 1/3  Finding hitters & pitchers who are quietly getting good...")
    hits = find_breakouts_multi(
        year=args.year,
        min_pa_batter=args.min_pa,
        min_pa_pitcher=args.min_pa_pitcher,
        top=args.top,
        types=types,
        starters_only=not args.include_relievers,
    )
    if not hits:
        print("  Couldn't reach Baseball Savant. Check your internet and try again.")
        return 1
    print(f"  Found {len(hits)} candidates.")

    print("Step 2/3  Checking who's still under the radar (Google Trends)...")
    hits = add_hype(hits, anchor=args.anchor)
    if all(h.interest is None for h in hits):
        print("  (Trends unavailable — showing breakout order. `pip install pytrends` to enable.)")
    hits = hits[: args.top]

    if not args.no_prices:
        print("Step 3/3  Checking real card prices on eBay...")
        hits = add_prices(hits)
        if all(h.median_price is None for h in hits):
            print("  (No eBay prices came back — likely blocked on this connection.)")
    else:
        print("Step 3/3  Skipped (--no-prices).")

    print("\n" + "=" * 62)
    print(f"  YOUR SLEEPER LIST — top {len(hits)}")
    print("=" * 62 + "\n")
    for i, h in enumerate(hits, 1):
        age = f"age {h.age}" if h.age is not None else "age ?"
        hype = f"{h.interest:.0f}% hype" if h.interest is not None else "hype ?"
        score = h.deal_score if h.deal_score is not None else (
            h.sleeper_score if h.sleeper_score is not None else h.score
        )
        label = "deal" if h.deal_score is not None else "sleeper"
        print(f"{i:>2}. {h.batter.name:<22} ({h.pos}) {label} {score:>4.0f}/100 | {age} | {hype}")
        print(f"    {h.reason}")
        if h.card_prices:
            cards = "  ".join(
                f"{lbl}: ${med:,.0f} ({cnt})" if med is not None else f"{lbl}: n/a"
                for lbl, (med, cnt) in h.card_prices.items()
            )
            print(f"    cards → {cards}")
        if h.price_trend is not None:
            if h.price_trend <= 0.05:
                print(f"    price still flat ({h.price_trend:+.0%}) — not late")
            elif h.price_trend >= 0.30:
                print(f"    price already +{h.price_trend:.0%} — likely LATE")
            else:
                print(f"    price moving (+{h.price_trend:.0%}) — window closing")
        print()

    print("How to read it: high deal score + young + low hype + card price still flat = buy early.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
