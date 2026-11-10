# Card Market: $100 / 30-day autonomous paper challenge

**Paper experiment only.** The bot never makes real purchases, places orders,
transfers funds, or claims a real completed trade.

## What it does

- Starts with $100 and scans once daily for 30 calendar days.
- Reuses the app's existing live MLB breakout + Google Trends + eBay sold-comps
  scanner, rather than its canned demo.
- Considers Bowman 1st auto and rookie auto reference-card categories.
- Requires deal score >= 50, breakout score >= 45, hype <= 30%, price momentum
  <= 15%, and 5 sold comps in the past 45 days, with a sale within 14 days.
  Missing or old data blocks purchases.
- Makes a *hypothetical* category-level reference purchase at the median recent
  sold price plus 5% simulated price slippage and $3.50 inbound shipping.
  This is NOT an available listing or an actual executable offer.
- Allows at most 1 buy/day, 5 positions, $25 all-in per position, and never
  more than 1 position per player. Unspent money remains in cash.
- Reprices holdings daily when fresh comparable sales exist.
- Reports estimated liquidation value after a 15% selling haircut plus $3.50
  outbound shipping, separately from cash; stale quotes make P&L unavailable.
- Stops opening positions after 30 days. It does not pretend the cards were
  physically acquired or sold.

**Critical limitation:** category searches can mix years, grades, conditions,
parallels and brands. Results are research-grade *proxy trading*, NOT a
validated executable-listing simulator. The future upgrade is exact variant
identification plus real active-listing URLs/prices, tax and shipping, and sales
of precisely comparable cards.

## Run commands

  python -m prehype.paper_bot run --ledger data/card_bot_100.json

  python -m prehype.paper_bot report --ledger data/card_bot_100.json

  python -m pytest tests/test_paper_bot.py -q

The GitHub Actions workflow (.github/workflows/card-bot-paper.yml) runs daily
at 14:30 UTC on the repository's DEFAULT branch after this feature is merged.
It also supports a manual workflow dispatch, and offline tests run on PRs.
It commits data/card_bot_100.json to the repo so state survives fresh runners.
The 30-day clock starts only when the live price feed provides at least one fresh, sufficiently liquid reference-card quote. If price data is missing, the daily job reports WAITING_FOR_LIVE_MARKET_DATA and does not create a ledger or consume a trial day.

## Requirements and limits

Live eBay sold comps are unreliable from GitHub-hosted/datacenter IPs. Unless
an authorized eBay Marketplace Insights token is available, the scan may have
no trustworthy price data and the bot WILL NOT BUY ANYTHING. If approved, set
EBAY_OAUTH_TOKEN in GitHub Actions Secrets; the existing eBay backend handles it.
The existing scraper supports EBAY_PROXY_URL as a fallback. Never commit tokens.
Google Trends may rate-limit or fail, and missing hype blocks entries.

The repository currently implements MLB prospect/breakout data only. In the
November offseason, player skill feeds are not updating with new games. This
is an exploratory paper test of candidate ranking and card-price monitoring,
not a cross-sport live-breakout bot.

## Monthly review

Read the daily ledger, card categories chosen, cash remaining, estimated
net liquidation, pricing freshness and rejection/no-trade days. This is not
realized profit, and a 30-day experiment is not statistical proof of an edge.
The trading rules are frozen for the trial, avoiding retrospective tuning.

## Live prices: now using Soldgraph (key required)

The first live scan discovered 15 MLB candidates but no card prices because the
original eBay scraper is blocked or fails on cloud hosts. The bot now has a
provider for both eBay **sold** listings and **active Buy It Now** offers.

**Activate it:**

1. Create a key at https://soldgraph.com/ (third-party service).
2. In the GitHub repository go to **Settings -> Secrets and variables ->
   Actions -> New repository secret**.
3. Name it exactly **SOLDGRAPH_KEY** and paste the value. Do not send the
   key in chat, in issues, or in code.
4. Under **Actions -> Card Bot $100 Paper Month**, select **Run workflow**.
5. Read **CARD_BOT_DASHBOARD.md** and the **Live pricing diagnostics** section.

A new Soldgraph account currently advertises **100 free searches total** (one
time, not monthly). Each screened reference requires **two** queries: recent
sold and active listings. To conserve this allowance, the bot checks **one
player-card pair each day** (or refreshes one held exact card by a single sold
query) and rotates the shortlist. The monitor persists checked dates and
requests in data/card_bot_market_monitor.json. Never enable a paid plan
without deciding whether its fees are worth the experiment.

**Buy conditions:** same named player, year, set, raw autograph and card
number across comparable sales and an actual eBay fixed-price listing; 5
matching sold transactions in 45 days including 2 from each half and 1 in
the last 14 days; reject unknown shipping, slabs, numbered parallels,
reprints, auctions, accepted Best Offers with unknown actual sold prices and
mismatched grades/variants. The bot records the active listing URL and
snapshot ask, known shipping, and 6% *estimated* sales tax. It also requires
at least $2 theoretical room after a 15% selling-fee allowance and $3.50
outbound shipping. Nothing is purchased from eBay.

**Limits:** These are listing snapshots and title-based matches, NOT
confirmed actual available inventory at a checkout. Conditions and seller
details may differ. The code does not capture true destination-dependent
shipping/tax or exact final sale prices. Zero buys with valid data is an
honest possible outcome.

The 30-day clock does not start until at least one sufficiently matched,
priced ACTIVE listing and sold history becomes available. Before that the
daily monitor and scouting board will still update. P&L uses the newest
qualifying same-variant sold marks within 7 days, never assumed realized gains.
