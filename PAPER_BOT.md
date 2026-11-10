# Card Market: $100 / 30-day autonomous paper challenge

## Full-season skill evolution — now active

The daily GitHub scout no longer discards games outside the final 84-game
window. For each of up to 88 **raw-stat-selected** MiLB hitters, it preserves
**every available 2026 regular-season player game** from the first to the
last. The list of 88 is a preselected sample, **not all 3,527 MiLB season
records**. This is a transparent coverage limit.

The new source-only development tracker records:

- **Complete per-game history:** official player date, game ID, team,
  plate appearances, at-bats, hits, doubles, triples, HR, walks, strikeouts,
  and other available hitting counts.
- **Chronological non-overlapping 14-game blocks** from season start through
  season end, including the final partial block, with PA, AVG/OBP/SLG/OPS,
  ISO, K%, BB%, HR and contact opportunity counts.
- **Every-seven-game checkpoints** with rolling 7-, 14- and 28-game
  performance, plus cumulative season and current-team totals.
- **As-of evidence events** identifying the first observed uptrend,
  the later falloff, flat/unclear stretches, and potential rebounds.
  Earlier uptrends that no longer qualify for an early breakout TODAY
  are retained in a separate cooling/regressing research table.
- **Context guards:** games are never mixed across different teams or
  lengthy 21+-day gaps in a single before/after comparison. Full-season
  history still includes the games on both sides of any change.
- **Previous 14v14, 28v28 and 42v42 checks** remain as recent
  evidence and sample-quality gates. They do not replace the
  full-season timeline.

Detailed data is automatically published at
[data/card_bot_full_season_latest.json](data/card_bot_full_season_latest.json);
the human-readable highlights appear in
[CARD_BOT_DASHBOARD.md](CARD_BOT_DASHBOARD.md). These histories show
*what was observed up to each date*, not that the bot successfully
predicted the move at that earlier date. There is no retrospective
backfilling of future games into earlier checkpoints.

**These phases are descriptive, not calibrated breakout odds.** The
current 2026 regular-season MiLB record is already finished in November.
Collector attention and usable exact-card prices remain unverified.
The $100 paper bankroll does not buy on season-history scores.

## Mission: find early talent BEFORE mainstream card hype

The bot's previous MLB season-over-season xwOBA leaderboard was not a
pre-hype prospect radar. That funnel could rank already prominent players.
As of November 10, 2026, discovery is rebuilt around **MiLB hitters**.

The live source is the official **free MLB StatsAPI**. The detector
looks for early skill change with **three historical horizons**: the most
recent 14 games versus the preceding 14 (28 games), the most recent 28 versus
the preceding 28 (56 games), and the most recent 42 versus the preceding 42
(**84 games maximum**). The comparison uses K% (plate contact/discipline),
BB% (strike-zone recognition) and ISO (extra-base-hit power), requiring two
distinct improved skills for an early watch signal. All comparisons use
non-overlapping before/after halves at the *same team* and minimum plate
appearances, avoiding accidental promotion-driven comparisons.

Each player receives a transparent **reliability tier**:
- **EARLY — not confirmed:** the 14-game signal is present, but a longer
  comparison is not yet testable. Watch for the next games.
- **SHORT SPIKE — not confirmed:** 14-game change looks promising but
  28-game confirmation disagrees. Possible noise or a newer, still-unproven
  shift; *not* a validated breakout.
- **BUILDING:** 14- and 28-game comparisons show multiple supported skill
  changes; an 84-game test may be unavailable.
- **SUSTAINED:** the 14-, 28-, and 42-game before/after comparisons all
  support improvements. The windows overlap, so this is **not** three
  independent statistical tests.
- **LONG WINDOW CONFLICT:** short and middle periods improve, but the
  longest comparison points to mixed, potentially reversible evidence.

A weak beta-binomial prior estimates *directional evidence* for K% and BB%,
while a deterministic game bootstrap tests how often a positive ISO change
persists when **games** are resampled. The outputs explicitly **are NOT
calibrated probabilities of future player breakouts or investment profit**.
Ranks give more weight to persistent signals and discount isolated spikes.
Age/level and sample-size guards remain. Forward-season holdouts are still
needed before any classification should be trusted as predictive.

During the offseason these are reviews of **2026 played games**, not new
November games. No new account, API token or paid service is used.

**Already known?** A public MLB Pipeline Top-100 ranking is a veto,
not a discovery source. We use publicly visible rankings only to identify
players who have already attracted mainstream prospect attention. A name
not appearing on that list is **not proof** it is un-hyped among collectors.
Card-specific collector attention, and exact listed/sold prices, must be
established separately before a buy can be authorized. Google searches
relative to Aaron Judge are NOT a valid collector-hype test.

The output separates:
1. **Early skill evidence:** recent underlying skill-change and uncertainty.
2. **Prior recognition:** major-league playing-time and public ranking vetoes.
3. **Card price and hobby hype:** often UNKNOWN with free sources; no fake cheap
   prices or simulated trades from incomplete card-value guides.

**November is the MiLB offseason.** The newest 2026 player games were months
ago. The report explicitly labels this as a retrospective 2026 candidate list
for offseason follow-up, not a real-time November breakout.

The current leading-signal radar covers MiLB **hitters**. Minor-league
pitcher-specific velocity, K/BB, pitch mix and workload tracking have not
been implemented; pretending those are already measured would be misleading.
The user needs NO new account or API key. Github Actions refreshes the
board daily. The $100 challenge remains paper-only and cannot start until
a genuinely actionable, affordable, underpriced player card is verified.

> **November 10 price/hype integrity alert:** The old catalog displayed a
> plausible-looking $18.02 mark for a Jac Caglianone Bowman autograph while
> independently published graded references were in the hundreds. The previous
> "hypePct" was merely Google searches relative to Aaron Judge, not card hype.
> The board now **quarantines all unverified vendor prices and collector-hype
> claims**. The $100 paper-trading clock and purchases remain paused until
> source-specific market value AND collector attention are defensibly validated.
> See [MARKET_DATA_AUDIT.md](MARKET_DATA_AUDIT.md).

**Paper experiment only.** The bot never makes real purchases, places orders,
transfers funds, or claims a real completed trade.

## What the active bot actually does

- Starts with $100 in **paper money only**.
- Uses official 2026 minor-league **player game logs** to find two-window skill changes before adding card references.
- Uses CardPricer's **public anonymous API** for reference identities,
  but does not trust or display its dollar price marks as market values.
- Does not call a guide price a real trade. Every eligible buy requires at
  least five source-linked, individually validated **sales of the exact
  card/grade** during the previous 30 days, with recent activity in both
  halves of the window and a sale in the last 14 days.
- Requires deal score >= 50, breakout score >= 45, verified market
  pricing and *independently validated card-collector interest*. The old
  Google Trends ratio versus Aaron Judge DOES NOT satisfy the last gate.
  Missing data blocks paper purchases.
- Simulates an exact-card **sold-median reference fill** plus 10% slippage and
  $3.50 inbound shipping. This is **NOT** a real offered listing or executable
  bid; transaction feasibility is not proven.
- Never spends more than $25 all-in on a card, opens more than one paper
  position a day, holds more than five positions or exceeds its $100 bank.
- Tracks remaining cash, card identity and audit link. It revalues holdings
  from exact-card sold records where sufficiently fresh.
- Estimates liquidation after 15% selling fees and $3.50 outbound shipping;
  no realized profits, real orders, real inventory or real sales are implied.
- Stops opening new positions 30 days after a fully qualified,
  independently market-verified card starts the experiment. The clock does not
  start merely because a guide price or skill-change signal exists.

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

