# Data-integrity audit: false card values and misleading "hype"

**Audit performed:** November 10, 2026. This is an incident report, not an endorsement of any data provider.

## Finding 1 — prices cannot be relied on

The November 10 scout displayed a nominal **$18.02 catalog mark** for
Jac Caglianone's 2024 Bowman Draft Chrome Prospect Autographs #CPAJC (MINT 9).
Public secondary-market references for the 2024 Bowman Draft Chrome Prospect
Autograph #CPA-JC place recent PSA Grade 9 prices in the **hundreds of
dollars** (a SportsCardsPro Grade 9 guide around $272.50 at audit time).

Independent reference:
https://www.sportscardspro.com/game/baseball-cards-2024-bowman-draft-chrome-prospect-autograph/jac-caglianone-cpa-jc

The original source said only "MINT 9" — NOT the grading company or parallel.
Therefore it cannot be assumed to be the exact same variant as PSA 9.
This is not evidence of an $18 bargain. It is evidence of **unreliable or
insufficiently identified catalog data**.

**Fixes deployed:**
- All unverified catalog dollar amounts are **hidden from the human scouting
  board** and retained only as catalog_raw_untrusted_usd in JSON for auditing.
- The reference discovery filter no longer drops cards with catalog mark above
  $22. That threshold biased discovery toward misleading cheap-looking base
  cards and away from the collector-relevant autograph targets.
- Autographs and Bowman references are prioritized by *identity*, not price.
- A source title with "MINT 9" but no grader name is not eligible for same-card
  comp validation. Provenance matching requires exact year, player, set,
  card number, grader, grade and non-parallel variant, plus time-split and
  independently referenced sold records.
- The actual *execution* price cannot be established from a sold median;
  any paper fill remains a labeled proxy, not a buyable listing.

## Finding 2 — "hypePct" wasn't a collector-hype percentage

The implementation in prehype/sources/trends.py compares each player-name
Google Trends mean to **Aaron Judge** over the last three months:

    reported value = average trend index for player / average index for Aaron Judge * 100

That is **relative search activity** — NOT share of card market interest,
a probability of low hype, or a validated signal of card-market lag. A heavily
collected prospect can appear at 1%–5% compared with a global superstar.

**Fixes deployed:**
- Initial player discovery ranks by actual Statcast *skill change*, not by
  the mislabeled search-hype ratio.
- The ratio is labeled Searches vs. Aaron Judge on the board as diagnostic
  information only.
- cardHypeVerified remains false until real collector-demand evidence can
  be obtained and validated.
- No paper buy and no 30-day countdown starts with collector hype unverified,
  regardless of a potentially attractive price guide or skill-change score.
- Zero source coverage is reported as unknown; never "low hype."

## Remaining work

This bot has **not** established authenticated collector attention, actionable
same-variant active offers, or repeatable acquisition economics. To go beyond a
scouting watchlist, it needs valid source coverage of actual card-specific
sales, listings and attention. Do not force paper trades by relaxing these
requirements or substituting baseball performance for card pricing.

The $100 simulation is still **paper-only**; no real money is deployed.
