# Card Market: $100 / 30-day autonomous paper challenge

**Paper experiment only.** The bot never makes real purchases, places orders,
transfers funds, or claims a real completed trade.

## What the active bot actually does

- Starts with $100 in **paper money only**.
- Uses MLB skill-change data and Google Trends to rank up to 30 players.
- Uses CardPricer's **public anonymous API** for a catalog of real card
  references (player, year, set, card number, grade and guide price).
- Does not call a guide price a real trade. Every eligible buy requires at
  least five source-linked, individually validated **sales of the exact
  card/grade** during the previous 30 days, with recent activity in both
  halves of the window and a sale in the last 14 days.
- Requires deal score >= 50, breakout score >= 45, hype <= 30% and verified
  card-price trend <= 15%. Missing data means no paper purchase.
- Simulates an exact-card **sold-median reference fill** plus 10% slippage and
  $3.50 inbound shipping. This is **NOT** a real offered listing or executable
  bid; transaction feasibility is not proven.
- Never spends more than $25 all-in on a card, opens more than one paper
  position a day, holds more than five positions or exceeds its $100 bank.
- Tracks remaining cash, card identity and audit link. It revalues holdings
  from exact-card sold records where sufficiently fresh.
- Estimates liquidation after 15% selling fees and $3.50 outbound shipping;
  no realized profits, real orders, real inventory or real sales are implied.
- Stops opening new positions 30 days after a qualifying priced card starts
  the experiment. If the feed remains too thin, the clock does not start.

**Critical limitation:** Many promising MLB players aren't yet covered by
the public catalog. Certain public price-series matches were incorrectly
attributed to similarly named cards; our independent title-matching gate
rejects those. The real experiment may make zero paper purchases.

## Run commands

  python -m prehype.paper_bot run --ledger data/card_bot_100.json

  python -m prehype.paper_bot report --ledger data/card_bot_100.json

  python -m pytest tests/test_paper_bot.py -q

The GitHub Actions workflow (.github/workflows/card-bot-paper.yml) runs daily
at 14:30 UTC on the repository's DEFAULT branch after this feature is merged.
It also supports a manual workflow dispatch, and offline tests run on PRs.
It commits data/card_bot_100.json to the repo so state survives fresh runners.
The 30-day clock starts only when the live price feed provides at least one fresh, sufficiently liquid reference-card quote. If price data is missing, the daily job reports WAITING_FOR_EXACT_CARD_SOLD_COMPS and does not create a ledger or consume a trial day.

## Requirements and limits

No additional accounts, API keys, paid plans or proxies are required.
The existing eBay HTML scraper and key-based Soldgraph adapter are **not**
used by the active paper bot. CardPricer's public API has uneven sports-card
coverage and its eBay ingestion currently reports zero recent records;
source provenance and on-field MLB signals determine what can be monitored.
November is baseball offseason, so there are no new live games feeding
skill-change discovery. Nothing in this run should be described as a
guaranteed executable card investment.

## Monthly review

Read the daily ledger, card categories chosen, cash remaining, estimated
net liquidation, pricing freshness and rejection/no-trade days. This is not
realized profit, and a 30-day experiment is not statistical proof of an edge.
The trading rules are frozen for the trial, avoiding retrospective tuning.

## Live card prices — now entirely account-free

The GitHub Actions runner uses CardPricer's **documented public anonymous API**:
https://cardpricer.co/docs/api. No signup, API token, secret, credit card,
proxy, paid plan, manual download, or other user's account is required. An
actual GitHub-hosted probe on November 9, 2026 returned HTTP 200 for its
baseball directory, recent-sales feed and data-freshness endpoint.

**How to run:** GitHub -> Actions -> Card Bot $100 Paper Month -> Run workflow.
The report updates CARD_BOT_DASHBOARD.md and data/card_bot_scouting_latest.json
after a successful run, even when no purchase can be justified.

The system reuses real on-field MLB data to rank up to 30 players, then checks
their published baseball card directory records. A catalog guide price is
displayed for information only. **Catalog prices cannot trigger trades.**

Before any paper buy, it fetches that exact card's provenance and independently
checks at least five RECENT completed sale titles for the **same player, year,
set, card number and grading lane**. At least two sales must fall in each
half of the 30-day window, and the latest sale must be no more than 14 days old.
This matters: the public provider's matcher has occasionally attached sales
from unrelated sets/cards with only the same player and grade. Those are
rejected even if the provider's headline confidence looks high.

If a valid quote exists, this is **still a reference-only paper buy**. The
system cannot assert that anyone is currently selling that exact card for the
sold median. It records the card identity, comp provenance link and simulated
entry at the matched median + 10% slippage + $3.50 shipping; estimated
liquidation subtracts 15% selling fees and $3.50 shipping. Strict $25 all-in
position cap, five positions and one paper purchase per day still apply.

**Limitations:** At the time of the live November 9 test, CardPricer's baseball
catalog showed roughly 2,377 cards but direct eBay ingestion reported zero
recent records; active sources were mostly tokenized/graded card venues. Many
of the existing MLB shortlist players had zero coverage and some provenance
matches were invalid. The bot therefore may make **zero purchases**. That's
the honest result of this no-account source, not evidence of no market
opportunity. Do not confuse graded card guide prices with same-card sold
prices or eBay available offers.

See https://cardpricer.co/docs/api for the source attribution and usage terms.
The repository retains the earlier Soldgraph integration as inactive legacy
code; it is not imported or used by the daily bot and **no user key is needed**.

