"""Command line entry point: ``python -m prehype scan``.

Prints a ranked watchlist of players whose cards look early — cheap, quiet, and
backed by a building breakout thesis.
"""

from __future__ import annotations

import argparse
import sys

from prehype.pipeline import scan
from prehype.scoring import ScoreWeights
from prehype.sources.base import DataSource
from prehype.sources.demo import DemoSource
from prehype.sources.mlb import MLBStatsSource
from prehype.sources.watchlist import WatchlistSource


def _build_sources(names: list[str], *, watchlist: str) -> list[DataSource]:
    sources: list[DataSource] = []
    for name in names:
        if name == "demo":
            sources.append(DemoSource())
        elif name == "mlb":
            sources.append(MLBStatsSource())
        elif name == "ebay":
            sources.append(WatchlistSource(watchlist))
        else:
            print(
                f"unknown source: {name!r} (have: demo, mlb, ebay)",
                file=sys.stderr,
            )
            raise SystemExit(2)
    return sources


def _cmd_scan(args: argparse.Namespace) -> int:
    sources = _build_sources(args.sources, watchlist=args.watchlist)
    signals = scan(
        sources,
        weights=ScoreWeights(),
        cheap_ref=args.cheap_ref,
        rich_ref=args.rich_ref,
        min_score=args.min_score,
        only_early=args.only_early,
    )

    if not signals:
        print("No candidates matched. Try lowering --min-score or adding a source.")
        return 0

    top = signals[: args.limit]
    print(f"\n=== Pre-Hype watchlist — {len(top)} of {len(signals)} candidates ===\n")
    for i, sig in enumerate(top, 1):
        print(f"{i}. {sig.as_alert()}\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="prehype",
        description="Find sports cards before the hype prices them in.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="scan sources and print the watchlist")
    s.add_argument(
        "--sources",
        nargs="+",
        default=["demo"],
        help="data sources to use (default: demo). Options: demo, mlb, ebay",
    )
    s.add_argument(
        "--watchlist",
        default="watchlist.json",
        help="path to watchlist JSON (used by the ebay source)",
    )
    s.add_argument("--limit", type=int, default=10, help="max rows to print")
    s.add_argument("--min-score", type=float, default=0.0, help="hide scores below this")
    s.add_argument(
        "--only-early",
        action="store_true",
        help="show only EARLY/WATCH plays (drop already-priced-in)",
    )
    s.add_argument("--cheap-ref", type=float, default=15.0, help="price considered 'dirt cheap'")
    s.add_argument("--rich-ref", type=float, default=500.0, help="price considered 'expensive'")
    s.set_defaults(func=_cmd_scan)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
