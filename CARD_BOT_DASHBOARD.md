# Card Bot — Daily Scouting Board

**Last scan:** 2026-11-11 | **Status:** EARLY_SKILL_WATCHLIST_OFFSEASON_NO_BUYS

**Paper-only experiment:** unverified catalog dollar values are HIDDEN. A verified same-card sale median is NOT an active offer. A player skill-change score is NOT an investment score.

**CHEAP ≠ AFFORDABLE:** a $10–$25 card is not a pre-hype bargain merely because it fits the bankroll. This paper strategy targets individually verified manufacturer-issued **1st Bowman autographs at $5 or less for the card and $10 or less delivered**. A genuine low-priced card is still not necessarily underpriced or unnoticed by collectors.

## Current paper bankroll

- Cash remaining: **USD 100.00**
- Paper purchases recorded: **0**
- Players considered today: **11**
- Estimated net liquidation, not realized: **USD 100.00**

## Paper holdings


## What the bot is actually hunting

**GOAL:** Younger MiLB players whose strikeout discipline, walk discipline and extra-base-hit production are improving *before* public recognition. This is **NOT** a ranked list of hyped MLB breakout stars.

- Discovery source: **Official MLB StatsAPI minor-league season stats and player game logs**
- Season reviewed: **2026**
- Context: **OFFSEASON / retrospectively reviewing last season (no new games today)**
- MiLB season rows read: **3527**
- Player game-log feeds with data: **88**
- Skill-change candidates: **20**
- Full-season tracking: **every available game** from first to last in a sampled player's season, including earlier streaks, slumps, rebounds and team changes
- Players with complete development histories: **88**
- Individual game observations retained: **8906**
- Compare all-season 14-game blocks plus **rolling 7/14/28-game checkpoints**, saved every seven games and at the last game
- Separate most recent comparison periods: **14v14, 28v28, 42v42** (up to 84 recent games); those overlapping horizons do not determine the entire seasonal history
- [**Open the full-season index**](data/card_bot_full_season_latest.json) to find one readable JSON file per player (all games, rolling checkpoints, phase events)
- Evidence tiers: **{'SUSTAINED_ACROSS_14_28_42': 0, 'BUILDING_14_AND_28': 0, 'EARLY_14_ONLY': 3, 'SHORT_SPIKE_NOT_CONFIRMED': 7, 'LONG_HORIZON_CONFLICT': 1}**
- Levels unavailable: **none**
- Major-league exposure filter: **available**
- A skill-change signal is NOT proof of low card-market hype or a fair card price.

### Already-publicized names removed from early shortlist

These players passed some raw skill-change checks, but are already publicly ranked prospects. **They are NOT pre-hype picks.**

| Player | Skill score (not probability) | Reason for exclusion |
|---|---:|---|
| Edward Florentino | 67.6 | [Already on a published Top-100 list](https://prospectpulsev1.com/pipeline/) |
| Demetrio Crisantes | 63.4 | [Already on a published Top-100 list](https://prospectpulsev1.com/pipeline/) |
| Dax Kilby | 58.0 | [Already on a published Top-100 list](https://prospectpulsev1.com/pipeline/) |
| Walker Jenkins | 54.9 | [Already on a published Top-100 list](https://prospectpulsev1.com/pipeline/) |
| Lazaro Montes | 53.2 | [Already on a published Top-100 list](https://prospectpulsev1.com/pipeline/) |
| Franklin Arias | 32.7 | [Already on a published Top-100 list](https://prospectpulsev1.com/pipeline/) |
| Josh Adamczewski | 44.7 | [Already on a published Top-100 list](https://prospectpulsev1.com/pipeline/) |
| Jesús Made | 43.5 | [Already on a published Top-100 list](https://prospectpulsev1.com/pipeline/) |
| Bryan Rincon | 37.7 | [Already on a published Top-100 list](https://prospectpulsev1.com/pipeline/) |


### Across the full season: what happened to every analyzed hitter?

These phase counts include **all sampled hitters**, not merely today's top breakout signals. A player who rose in June but fell in August remains in the research archive.

| Development phase (descriptive) | Players |
|---|---:|
| EARLIER UPTREND CURRENT WINDOW UNAVAILABLE | 21 |
| REGRESSING AFTER UPTREND | 20 |
| REBOUNDING AFTER DOWNTREND | 18 |
| EARLIER UPTREND NOW MIXED OR FLAT | 17 |
| INSUFFICIENT RECENT EVIDENCE | 6 |
| CURRENT UPTREND | 3 |
| CURRENT DOWNTREND | 2 |
| NO UPTREND DETECTED | 1 |


### Earlier season improvement that later faded or became unclear

**Research-only:** this is the falling-off / cooling-off detector. These names are **NOT** recommended card buys. Disappearing from today's breakout list does not mean the earlier improvement never occurred.

| Player | Level | Games tracked | Earlier uptrend first seen | Current phase | Last game |
|---|---|---:|---|---|---|
| [Leo Balcazar](data/card_bot_season_players/2026/699114.json) | AAA | 138 | 2026-07-31 | REGRESSING AFTER UPTREND | 2026-09-20 |
| [Caleb Bonemer](data/card_bot_season_players/2026/815352.json) | AA | 131 | 2026-05-06 | REGRESSING AFTER UPTREND | 2026-09-13 |
| [Eric Hartman](data/card_bot_season_players/2026/807080.json) | AA | 128 | 2026-05-07 | REGRESSING AFTER UPTREND | 2026-09-13 |
| [Carlos Sanchez](data/card_bot_season_players/2026/800176.json) | AA | 127 | 2026-05-08 | REGRESSING AFTER UPTREND | 2026-09-13 |
| [Ralphy Velazquez](data/card_bot_season_players/2026/806252.json) | AAA | 121 | 2026-05-08 | REGRESSING AFTER UPTREND | 2026-09-20 |
| [Nolan Schubart](data/card_bot_season_players/2026/702278.json) | AA | 119 | 2026-05-10 | REGRESSING AFTER UPTREND | 2026-09-13 |
| [Emil Morales](data/card_bot_season_players/2026/815896.json) | A+ | 117 | 2026-07-18 | REGRESSING AFTER UPTREND | 2026-09-05 |
| [Rainiel Rodriguez](data/card_bot_season_players/2026/823787.json) | AA | 115 | 2026-06-18 | REGRESSING AFTER UPTREND | 2026-09-12 |
| [Gabriel Gonzalez](data/card_bot_season_players/2026/694224.json) | AAA | 114 | 2026-05-01 | REGRESSING AFTER UPTREND | 2026-09-20 |
| [Michael Arroyo](data/card_bot_season_players/2026/703197.json) | AAA | 114 | 2026-06-25 | REGRESSING AFTER UPTREND | 2026-09-05 |
| [Mikey Romero](data/card_bot_season_players/2026/702540.json) | AAA | 113 | 2026-06-26 | REGRESSING AFTER UPTREND | 2026-09-19 |
| [Ryan Mitchell](data/card_bot_season_players/2026/815829.json) | A | 107 | 2026-05-13 | REGRESSING AFTER UPTREND | 2026-09-06 |
| [Xavier Neyens](data/card_bot_season_players/2026/815832.json) | A | 103 | 2026-05-15 | REGRESSING AFTER UPTREND | 2026-09-06 |
| [Kevin Alvarez](data/card_bot_season_players/2026/829037.json) | A | 99 | 2026-05-16 | REGRESSING AFTER UPTREND | 2026-09-05 |
| [Conor Essenburg](data/card_bot_season_players/2026/828148.json) | A+ | 93 | 2026-07-21 | REGRESSING AFTER UPTREND | 2026-09-06 |
| [Brailyn Antunez](data/card_bot_season_players/2026/829073.json) | A | 92 | 2026-06-20 | REGRESSING AFTER UPTREND | 2026-09-06 |
| [Luis Arana](data/card_bot_season_players/2026/829854.json) | A | 81 | 2026-08-12 | REGRESSING AFTER UPTREND | 2026-09-05 |
| [Gage Miller](data/card_bot_season_players/2026/824028.json) | AAA | 80 | 2026-05-22 | REGRESSING AFTER UPTREND | 2026-09-19 |
| [Franklin Primera](data/card_bot_season_players/2026/829398.json) | A | 78 | 2026-09-01 | REGRESSING AFTER UPTREND | 2026-09-06 |
| [Jose Silva](data/card_bot_season_players/2026/834925.json) | A | 58 | 2026-08-14 | REGRESSING AFTER UPTREND | 2026-09-04 |
More histories (38) are in the full-season JSON.


## Live pricing diagnostics

- Provider: **[CardPricer public anonymous API](https://cardpricer.co)** (no key/account)
- HTTP requests this scan: **13**
- MLB players checked for public cards: **11**
- Catalog cards discovered: **2**
- Exact variant prices with >=5 independently title-matched sales: **0**
- Feed status: **No API error reported**
- Catalog price estimates: **QUARANTINED / NOT SHOWN** (independent values disagreed substantially).
- Card-collector hype: **NOT VERIFIED**. Google search interest relative to Aaron Judge is not card demand.
- Paper buying from unverified card-attention data: **BLOCKED**.

No paper holdings yet.

## Players considered

**Early-signal strength is a heuristic, NOT a profit probability.** Longer-window evidence is ranked ahead of short-lived spikes. None are confirmed cheap or unnoticed cards.

| Evidence rank | Player | Level | Age | Games tracked | Full-season phase | Latest persistence tier | Heuristic score | Per-game file |
|---:|---|---|---:|---:|---|---|---:|---|
| 1 | Sebastian Dos Santos | A | 18 | 82 | CURRENT UPTREND | EARLY — not confirmed | 62.8 | [Full season](data/card_bot_season_players/2026/829741.json) |
| 2 | Luis Escudero | A | 20 | 58 | REBOUNDING AFTER DOWNTREND | EARLY — not confirmed | 54.2 | [Full season](data/card_bot_season_players/2026/806884.json) |
| 3 | Josiah Ragsdale | AA | 22 | 116 | REBOUNDING AFTER DOWNTREND | EARLY — not confirmed | 43.3 | [Full season](data/card_bot_season_players/2026/828824.json) |
| 4 | Johanfran Garcia | AA | 21 | 80 | REBOUNDING AFTER DOWNTREND | SHORT SPIKE — not confirmed | 45.8 | [Full season](data/card_bot_season_players/2026/703190.json) |
| 5 | Handelfry Encarnacion | A | 19 | 111 | REBOUNDING AFTER DOWNTREND | SHORT SPIKE — not confirmed | 42.4 | [Full season](data/card_bot_season_players/2026/821136.json) |
| 6 | Jaison Chourio | AA | 21 | 115 | REBOUNDING AFTER DOWNTREND | LONG WINDOW CONFLICT | 39.7 | [Full season](data/card_bot_season_players/2026/702693.json) |
| 7 | Andrew Fischer | AA | 22 | 126 | REBOUNDING AFTER DOWNTREND | SHORT SPIKE — not confirmed | 38.6 | [Full season](data/card_bot_season_players/2026/702652.json) |
| 8 | Starlyn Caba | A+ | 20 | 81 | REBOUNDING AFTER DOWNTREND | SHORT SPIKE — not confirmed | 38.2 | [Full season](data/card_bot_season_players/2026/806965.json) |
| 9 | Zach Ehrhard | AAA | 23 | 138 | REBOUNDING AFTER DOWNTREND | SHORT SPIKE — not confirmed | 35.0 | [Full season](data/card_bot_season_players/2026/701394.json) |
| 10 | Cristofer Torin | AA | 21 | 118 | REBOUNDING AFTER DOWNTREND | SHORT SPIKE — not confirmed | 28.8 | [Full season](data/card_bot_season_players/2026/800198.json) |
| 11 | Aroon Escobar | AA | 21 | 132 | REBOUNDING AFTER DOWNTREND | SHORT SPIKE — not confirmed | 25.2 | [Full season](data/card_bot_season_players/2026/800169.json) |

## Multi-window skill evidence — fluke or sustained?

Each row compares the most recent N games against the **immediately preceding N games**. All data are as of the scan date and must remain on the same MiLB team. Horizons overlap; confidence-support figures are descriptive, **NOT** probabilities of future breakout.

| Player | Window | Before → after K% | Before → after BB% | Before → after ISO | Supported metrics | Result |
|---|---|---|---|---|---|---|
| Sebastian Dos Santos | 14 vs 14 (61/63 PA) | 27.9% → 15.9% | 18.0% → 20.6% | 0.163 → 0.400 | K, ISO | SUPPORTS CHANGE |
| Sebastian Dos Santos | 28 vs 28 | — | — | — | — | TEAM CHANGE |
| Sebastian Dos Santos | 42 vs 42 | — | — | — | — | INSUFFICIENT GAMES |
| Luis Escudero | 14 vs 14 (53/54 PA) | 20.8% → 9.3% | 17.0% → 18.5% | 0.140 → 0.262 | K, ISO | SUPPORTS CHANGE |
| Luis Escudero | 28 vs 28 | — | — | — | — | TEAM CHANGE |
| Luis Escudero | 42 vs 42 | — | — | — | — | INSUFFICIENT GAMES |
| Josiah Ragsdale | 14 vs 14 (66/66 PA) | 30.3% → 21.2% | 12.1% → 13.6% | 0.161 → 0.148 | K | NOT CONFIRMED |
| Josiah Ragsdale | 28 vs 28 | — | — | — | — | TEAM CHANGE |
| Josiah Ragsdale | 42 vs 42 | — | — | — | — | TEAM CHANGE |
| Johanfran Garcia | 14 vs 14 (57/64 PA) | 40.4% → 29.7% | 7.0% → 12.5% | 0.157 → 0.273 | K, BB, ISO | SUPPORTS CHANGE |
| Johanfran Garcia | 28 vs 28 (121/121 PA) | 25.6% → 34.7% | 3.3% → 9.9% | 0.164 → 0.217 | BB | NOT CONFIRMED |
| Johanfran Garcia | 42 vs 42 | — | — | — | — | INSUFFICIENT GAMES |
| Handelfry Encarnacion | 14 vs 14 (65/68 PA) | 20.0% → 7.4% | 13.8% → 11.8% | 0.018 → 0.190 | K, ISO | SUPPORTS CHANGE |
| Handelfry Encarnacion | 28 vs 28 (134/133 PA) | 14.9% → 13.5% | 17.2% → 12.8% | 0.196 → 0.106 | none | NOT CONFIRMED |
| Handelfry Encarnacion | 42 vs 42 (207/202 PA) | 15.5% → 14.4% | 18.8% → 14.4% | 0.147 → 0.132 | none | NOT CONFIRMED |
| Jaison Chourio | 14 vs 14 (69/61 PA) | 26.1% → 14.8% | 15.9% → 13.1% | 0.018 → 0.096 | K, ISO | SUPPORTS CHANGE |
| Jaison Chourio | 28 vs 28 (124/130 PA) | 25.0% → 20.8% | 10.5% → 14.6% | 0.147 → 0.055 | K, BB | SUPPORTS CHANGE |
| Jaison Chourio | 42 vs 42 (186/196 PA) | 21.0% → 22.4% | 11.8% → 13.8% | 0.191 → 0.084 | none | NOT CONFIRMED |
| Andrew Fischer | 14 vs 14 (56/64 PA) | 37.5% → 28.1% | 5.4% → 31.2% | 0.440 → 0.419 | K, BB | SUPPORTS CHANGE |
| Andrew Fischer | 28 vs 28 (128/120 PA) | 33.6% → 32.5% | 16.4% → 19.2% | 0.262 → 0.430 | ISO | NOT CONFIRMED |
| Andrew Fischer | 42 vs 42 | — | — | — | — | TEAM CHANGE |
| Starlyn Caba | 14 vs 14 (62/60 PA) | 30.6% → 25.0% | 17.7% → 21.7% | 0.080 → 0.213 | ISO | NOT CONFIRMED |
| Starlyn Caba | 28 vs 28 (135/122 PA) | 23.0% → 27.9% | 20.7% → 19.7% | 0.125 → 0.144 | none | NOT CONFIRMED |
| Starlyn Caba | 42 vs 42 | — | — | — | — | INSUFFICIENT GAMES |
| Zach Ehrhard | 14 vs 14 (63/66 PA) | 30.2% → 16.7% | 7.9% → 10.6% | 0.143 → 0.153 | K | NOT CONFIRMED |
| Zach Ehrhard | 28 vs 28 (136/129 PA) | 16.9% → 23.3% | 19.9% → 9.3% | 0.162 → 0.148 | none | NOT CONFIRMED |
| Zach Ehrhard | 42 vs 42 (195/199 PA) | 20.5% → 20.6% | 16.9% → 14.1% | 0.239 → 0.167 | none | NOT CONFIRMED |
| Cristofer Torin | 14 vs 14 (65/71 PA) | 12.3% → 8.5% | 4.6% → 9.9% | 0.200 → 0.206 | K, BB | SUPPORTS CHANGE |
| Cristofer Torin | 28 vs 28 (126/136 PA) | 11.9% → 10.3% | 8.7% → 7.4% | 0.091 → 0.203 | ISO | NOT CONFIRMED |
| Cristofer Torin | 42 vs 42 (196/199 PA) | 9.2% → 10.6% | 6.1% → 9.0% | 0.140 → 0.153 | BB | NOT CONFIRMED |
| Aroon Escobar | 14 vs 14 (57/57 PA) | 17.5% → 14.0% | 14.0% → 8.8% | 0.167 → 0.260 | none | NOT CONFIRMED |
| Aroon Escobar | 28 vs 28 (118/114 PA) | 16.9% → 15.8% | 11.0% → 11.4% | 0.081 → 0.214 | ISO | NOT CONFIRMED |
| Aroon Escobar | 42 vs 42 (190/172 PA) | 14.7% → 15.1% | 15.8% → 11.0% | 0.045 → 0.196 | ISO | NOT CONFIRMED |

## Full-season progression: 14-game blocks, beginning to end

Each line represents a **separate chronological block** of games. The final block may be shorter. Blocks never mix players' different teams or long layoffs; the full per-game audit also contains rolling 7/14/28-game checkpoints.

| Player | Team stint | Games in stint | Through | PA | AVG | OBP | SLG | ISO | K% | BB% | HR |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Sebastian Dos Santos | 1 / 1370 | 1-14 | 2026-05-25 | 59 | 0.262 | 0.475 | 0.548 | 0.286 | 23.7% | 23.7% | 2 |
| Sebastian Dos Santos | 1 / 1370 | 15-27 (partial) | 2026-06-13 | 53 | 0.267 | 0.377 | 0.622 | 0.356 | 24.5% | 15.1% | 4 |
| Sebastian Dos Santos | 2 / 279 | 1-14 | 2026-07-04 | 68 | 0.189 | 0.368 | 0.264 | 0.075 | 26.5% | 17.6% | 1 |
| Sebastian Dos Santos | 2 / 279 | 15-28 | 2026-07-26 | 67 | 0.218 | 0.343 | 0.364 | 0.145 | 23.9% | 13.4% | 2 |
| Sebastian Dos Santos | 2 / 279 | 29-42 | 2026-08-18 | 62 | 0.292 | 0.452 | 0.458 | 0.167 | 27.4% | 19.4% | 2 |
| Sebastian Dos Santos | 2 / 279 | 43-55 (partial) | 2026-09-06 | 58 | 0.302 | 0.448 | 0.721 | 0.419 | 15.5% | 19.0% | 5 |
| Luis Escudero | 1 / 475 | 1-6 (partial) | 2026-05-22 | 25 | 0.222 | 0.440 | 0.389 | 0.167 | 20.0% | 24.0% | 1 |
| Luis Escudero | 2 / 587 | 1-14 | 2026-06-19 | 57 | 0.286 | 0.456 | 0.524 | 0.238 | 19.3% | 24.6% | 2 |
| Luis Escudero | 2 / 587 | 15-28 | 2026-07-26 | 53 | 0.256 | 0.453 | 0.615 | 0.359 | 22.6% | 26.4% | 4 |
| Luis Escudero | 2 / 587 | 29-42 | 2026-08-20 | 58 | 0.298 | 0.431 | 0.532 | 0.234 | 13.8% | 15.5% | 3 |
| Luis Escudero | 2 / 587 | 43-52 (partial) | 2026-09-06 | 34 | 0.320 | 0.500 | 0.560 | 0.240 | 8.8% | 23.5% | 1 |
| Josiah Ragsdale | 1 / 572 | 1-14 | 2026-04-22 | 53 | 0.200 | 0.377 | 0.375 | 0.175 | 30.2% | 22.6% | 1 |
| Josiah Ragsdale | 1 / 572 | 15-28 | 2026-05-12 | 62 | 0.302 | 0.393 | 0.491 | 0.189 | 22.6% | 12.9% | 2 |
| Josiah Ragsdale | 1 / 572 | 29-42 | 2026-05-30 | 63 | 0.340 | 0.468 | 0.400 | 0.060 | 27.0% | 19.1% | 0 |
| Josiah Ragsdale | 1 / 572 | 43-56 | 2026-06-24 | 66 | 0.400 | 0.500 | 0.654 | 0.255 | 25.8% | 13.6% | 2 |
| Josiah Ragsdale | 1 / 572 | 57-60 (partial) | 2026-06-28 | 20 | 0.438 | 0.550 | 1.000 | 0.562 | 0.0% | 15.0% | 2 |
| Josiah Ragsdale | 2 / 5015 | 1-14 | 2026-07-19 | 64 | 0.298 | 0.484 | 0.553 | 0.255 | 23.4% | 26.6% | 3 |
| Josiah Ragsdale | 2 / 5015 | 15-26 (partial) | 2026-08-02 | 55 | 0.286 | 0.364 | 0.837 | 0.551 | 36.4% | 10.9% | 9 |
| Josiah Ragsdale | 3 / 440 | 1-14 | 2026-08-21 | 66 | 0.214 | 0.303 | 0.393 | 0.179 | 31.8% | 12.1% | 2 |
| Josiah Ragsdale | 3 / 440 | 15-28 | 2026-09-11 | 66 | 0.283 | 0.424 | 0.491 | 0.207 | 15.2% | 15.2% | 3 |
| Josiah Ragsdale | 3 / 440 | 29-30 (partial) | 2026-09-13 | 9 | 0.125 | 0.222 | 0.125 | 0.000 | 55.6% | 11.1% | 0 |
| Johanfran Garcia | 1 / 546 | 1-14 | 2026-05-14 | 61 | 0.196 | 0.262 | 0.482 | 0.286 | 27.9% | 6.6% | 5 |
| Johanfran Garcia | 1 / 546 | 15-28 | 2026-06-03 | 62 | 0.328 | 0.371 | 0.552 | 0.224 | 29.0% | 4.8% | 4 |
| Johanfran Garcia | 1 / 546 | 29-42 | 2026-06-25 | 64 | 0.400 | 0.438 | 0.583 | 0.183 | 26.6% | 4.7% | 2 |
| Johanfran Garcia | 1 / 546 | 43-56 | 2026-07-30 | 56 | 0.222 | 0.250 | 0.315 | 0.093 | 28.6% | 1.8% | 1 |
| Johanfran Garcia | 1 / 546 | 57-70 | 2026-08-27 | 59 | 0.250 | 0.322 | 0.385 | 0.135 | 30.5% | 8.5% | 2 |
| Johanfran Garcia | 1 / 546 | 71-80 (partial) | 2026-09-12 | 46 | 0.300 | 0.391 | 0.675 | 0.375 | 37.0% | 13.0% | 4 |
| Handelfry Encarnacion | 1 / 249 | 1-14 | 2026-04-19 | 63 | 0.157 | 0.318 | 0.294 | 0.137 | 28.6% | 15.9% | 1 |
| Handelfry Encarnacion | 1 / 249 | 15-28 | 2026-05-06 | 64 | 0.259 | 0.375 | 0.574 | 0.315 | 23.4% | 15.6% | 4 |
| Handelfry Encarnacion | 1 / 249 | 29-42 | 2026-05-24 | 69 | 0.185 | 0.362 | 0.296 | 0.111 | 17.4% | 18.8% | 1 |
| Handelfry Encarnacion | 1 / 249 | 43-56 | 2026-06-11 | 73 | 0.298 | 0.438 | 0.368 | 0.070 | 17.8% | 19.2% | 0 |
| Handelfry Encarnacion | 1 / 249 | 57-70 | 2026-06-27 | 64 | 0.321 | 0.422 | 0.547 | 0.226 | 10.9% | 15.6% | 2 |
| Handelfry Encarnacion | 1 / 249 | 71-84 | 2026-07-21 | 69 | 0.296 | 0.435 | 0.463 | 0.167 | 17.4% | 17.4% | 2 |
| Handelfry Encarnacion | 1 / 249 | 85-98 | 2026-08-08 | 66 | 0.164 | 0.288 | 0.236 | 0.073 | 18.2% | 15.2% | 1 |
| Handelfry Encarnacion | 1 / 249 | 99-111 (partial) | 2026-08-28 | 63 | 0.315 | 0.381 | 0.463 | 0.148 | 7.9% | 11.1% | 1 |
| Jaison Chourio | 1 / 437 | 1-14 | 2026-04-21 | 68 | 0.309 | 0.426 | 0.509 | 0.200 | 16.2% | 17.6% | 2 |
| Jaison Chourio | 1 / 437 | 15-22 (partial) | 2026-05-03 | 34 | 0.333 | 0.441 | 0.407 | 0.074 | 20.6% | 17.6% | 0 |
| Jaison Chourio | 2 / 402 | 1-14 | 2026-06-04 | 62 | 0.321 | 0.410 | 0.491 | 0.170 | 14.5% | 12.9% | 2 |
| Jaison Chourio | 2 / 402 | 15-28 | 2026-06-21 | 62 | 0.314 | 0.435 | 0.549 | 0.235 | 14.5% | 17.7% | 2 |
| Jaison Chourio | 2 / 402 | 29-42 | 2026-07-08 | 60 | 0.211 | 0.300 | 0.327 | 0.115 | 31.7% | 11.7% | 1 |
| Jaison Chourio | 2 / 402 | 43-56 | 2026-07-28 | 64 | 0.241 | 0.312 | 0.345 | 0.103 | 23.4% | 9.4% | 1 |
| Jaison Chourio | 2 / 402 | 57-70 | 2026-08-13 | 66 | 0.190 | 0.277 | 0.310 | 0.121 | 22.7% | 10.6% | 1 |
| Jaison Chourio | 2 / 402 | 71-84 | 2026-09-04 | 68 | 0.304 | 0.418 | 0.375 | 0.071 | 25.0% | 16.2% | 0 |
| Jaison Chourio | 2 / 402 | 85-93 (partial) | 2026-09-13 | 38 | 0.290 | 0.395 | 0.355 | 0.065 | 13.2% | 15.8% | 0 |
| Andrew Fischer | 1 / 572 | 1-14 | 2026-04-21 | 60 | 0.255 | 0.367 | 0.404 | 0.149 | 35.0% | 13.3% | 1 |
| Andrew Fischer | 1 / 572 | 15-28 | 2026-05-10 | 66 | 0.288 | 0.364 | 0.797 | 0.508 | 37.9% | 9.1% | 8 |
| Andrew Fischer | 1 / 572 | 29-42 | 2026-05-29 | 67 | 0.277 | 0.492 | 0.617 | 0.340 | 26.9% | 23.9% | 5 |
| Andrew Fischer | 1 / 572 | 43-54 (partial) | 2026-06-13 | 53 | 0.395 | 0.566 | 0.895 | 0.500 | 34.0% | 28.3% | 6 |
| Andrew Fischer | 2 / 5015 | 1-14 | 2026-07-03 | 57 | 0.283 | 0.421 | 0.826 | 0.543 | 33.3% | 17.5% | 7 |
| Andrew Fischer | 2 / 5015 | 15-28 | 2026-07-23 | 62 | 0.220 | 0.355 | 0.420 | 0.200 | 33.9% | 16.1% | 2 |
| Andrew Fischer | 2 / 5015 | 29-42 | 2026-08-08 | 67 | 0.259 | 0.373 | 0.574 | 0.315 | 34.3% | 16.4% | 5 |
| Andrew Fischer | 2 / 5015 | 43-56 | 2026-08-25 | 56 | 0.170 | 0.250 | 0.447 | 0.277 | 35.7% | 10.7% | 4 |
| Andrew Fischer | 2 / 5015 | 57-70 | 2026-09-11 | 62 | 0.333 | 0.532 | 0.976 | 0.643 | 29.0% | 30.6% | 9 |
| Andrew Fischer | 2 / 5015 | 71-72 (partial) | 2026-09-13 | 10 | 0.333 | 0.400 | 0.667 | 0.333 | 20.0% | 10.0% | 1 |
| Starlyn Caba | 1 / 554 | 1-14 | 2026-04-22 | 64 | 0.302 | 0.406 | 0.491 | 0.189 | 21.9% | 14.1% | 2 |
| Starlyn Caba | 1 / 554 | 15-28 | 2026-05-14 | 66 | 0.207 | 0.364 | 0.321 | 0.113 | 21.2% | 18.2% | 1 |
| Starlyn Caba | 1 / 554 | 29-42 | 2026-06-24 | 69 | 0.245 | 0.420 | 0.434 | 0.189 | 24.6% | 23.2% | 2 |
| Starlyn Caba | 1 / 554 | 43-56 | 2026-07-17 | 66 | 0.235 | 0.394 | 0.314 | 0.078 | 22.7% | 19.7% | 0 |
| Starlyn Caba | 1 / 554 | 57-70 | 2026-08-08 | 61 | 0.157 | 0.295 | 0.294 | 0.137 | 31.1% | 14.8% | 1 |
| Starlyn Caba | 1 / 554 | 71-81 (partial) | 2026-08-25 | 47 | 0.286 | 0.468 | 0.429 | 0.143 | 23.4% | 25.5% | 1 |
| Zach Ehrhard | 1 / 238 | 1-14 | 2026-04-15 | 62 | 0.309 | 0.387 | 0.527 | 0.218 | 29.0% | 8.1% | 2 |
| Zach Ehrhard | 1 / 238 | 15-28 | 2026-05-01 | 68 | 0.190 | 0.235 | 0.224 | 0.035 | 19.1% | 7.3% | 0 |
| Zach Ehrhard | 1 / 238 | 29-42 | 2026-05-23 | 62 | 0.277 | 0.452 | 0.425 | 0.149 | 14.5% | 22.6% | 1 |
| Zach Ehrhard | 1 / 238 | 43-56 | 2026-06-09 | 64 | 0.396 | 0.500 | 0.641 | 0.245 | 14.1% | 17.2% | 3 |
| Zach Ehrhard | 1 / 238 | 57-70 | 2026-06-25 | 69 | 0.224 | 0.348 | 0.534 | 0.310 | 27.5% | 15.9% | 5 |
| Zach Ehrhard | 1 / 238 | 71-84 | 2026-07-17 | 58 | 0.312 | 0.431 | 0.542 | 0.229 | 19.0% | 15.5% | 3 |
| Zach Ehrhard | 1 / 238 | 85-98 | 2026-08-05 | 69 | 0.377 | 0.493 | 0.509 | 0.132 | 14.5% | 18.8% | 1 |
| Zach Ehrhard | 1 / 238 | 99-112 | 2026-08-21 | 68 | 0.288 | 0.456 | 0.462 | 0.173 | 16.2% | 22.1% | 2 |
| Zach Ehrhard | 1 / 238 | 113-126 | 2026-09-05 | 65 | 0.167 | 0.231 | 0.300 | 0.133 | 35.4% | 6.2% | 2 |
| Zach Ehrhard | 1 / 238 | 127-138 (partial) | 2026-09-20 | 55 | 0.417 | 0.491 | 0.604 | 0.188 | 10.9% | 12.7% | 1 |
| Cristofer Torin | 1 / 5368 | 1-14 | 2026-04-22 | 67 | 0.185 | 0.318 | 0.333 | 0.148 | 23.9% | 16.4% | 2 |
| Cristofer Torin | 1 / 5368 | 15-28 | 2026-05-14 | 67 | 0.230 | 0.284 | 0.344 | 0.115 | 10.4% | 4.5% | 1 |
| Cristofer Torin | 1 / 5368 | 29-42 | 2026-06-02 | 65 | 0.355 | 0.385 | 0.565 | 0.210 | 7.7% | 4.6% | 1 |
| Cristofer Torin | 1 / 5368 | 43-56 | 2026-06-19 | 67 | 0.224 | 0.298 | 0.362 | 0.138 | 3.0% | 9.0% | 2 |
| Cristofer Torin | 1 / 5368 | 57-70 | 2026-07-08 | 65 | 0.250 | 0.297 | 0.467 | 0.217 | 12.3% | 3.1% | 3 |
| Cristofer Torin | 1 / 5368 | 71-84 | 2026-07-28 | 62 | 0.207 | 0.306 | 0.264 | 0.057 | 12.9% | 12.9% | 1 |
| Cristofer Torin | 1 / 5368 | 85-98 | 2026-08-18 | 64 | 0.368 | 0.429 | 0.526 | 0.158 | 9.4% | 7.8% | 2 |
| Cristofer Torin | 1 / 5368 | 99-112 | 2026-09-04 | 70 | 0.429 | 0.478 | 0.667 | 0.238 | 11.4% | 8.6% | 3 |
| Cristofer Torin | 1 / 5368 | 113-118 (partial) | 2026-09-13 | 29 | 0.222 | 0.241 | 0.333 | 0.111 | 6.9% | 3.5% | 1 |
| Aroon Escobar | 1 / 522 | 1-14 | 2026-04-19 | 64 | 0.268 | 0.344 | 0.393 | 0.125 | 21.9% | 9.4% | 1 |
| Aroon Escobar | 1 / 522 | 15-28 | 2026-05-07 | 62 | 0.283 | 0.387 | 0.453 | 0.170 | 8.1% | 12.9% | 2 |
| Aroon Escobar | 1 / 522 | 29-42 | 2026-05-22 | 55 | 0.192 | 0.218 | 0.231 | 0.038 | 29.1% | 3.6% | 0 |
| Aroon Escobar | 1 / 522 | 43-56 | 2026-06-07 | 60 | 0.137 | 0.267 | 0.196 | 0.059 | 16.7% | 15.0% | 1 |
| Aroon Escobar | 1 / 522 | 57-70 | 2026-06-24 | 63 | 0.245 | 0.365 | 0.264 | 0.019 | 6.3% | 14.3% | 0 |
| Aroon Escobar | 1 / 522 | 71-84 | 2026-07-12 | 68 | 0.222 | 0.382 | 0.333 | 0.111 | 19.1% | 17.6% | 2 |
| Aroon Escobar | 1 / 522 | 85-98 | 2026-08-02 | 56 | 0.208 | 0.304 | 0.292 | 0.083 | 16.1% | 8.9% | 1 |
| Aroon Escobar | 1 / 522 | 99-112 | 2026-08-20 | 61 | 0.216 | 0.311 | 0.353 | 0.137 | 16.4% | 11.5% | 1 |
| Aroon Escobar | 1 / 522 | 113-126 | 2026-09-06 | 55 | 0.213 | 0.327 | 0.319 | 0.106 | 16.4% | 14.5% | 1 |
| Aroon Escobar | 1 / 522 | 127-132 (partial) | 2026-09-13 | 25 | 0.409 | 0.480 | 1.000 | 0.591 | 8.0% | 4.0% | 3 |

### When the rolling game statistics changed direction

Events below are **as-of observations** of a 14v14 comparison at the date shown—not predictions made on that date.

| Player | As of | Season game | Observed direction | K% Δ | BB% Δ | ISO Δ |
|---|---|---:|---|---:|---:|---:|
| Sebastian Dos Santos | 2026-07-26 | 55 | UPTREND | -2.6% | -4.2% | +0.070 |
| Sebastian Dos Santos | 2026-08-27 | 76 | UPTREND | -5.5% | +6.8% | +0.099 |
| Luis Escudero | 2026-07-26 | 34 | UPTREND | +3.3% | +1.9% | +0.121 |
| Luis Escudero | 2026-08-07 | 41 | DOWNTREND | +2.5% | -14.0% | -0.347 |
| Luis Escudero | 2026-09-03 | 55 | UPTREND | -8.1% | +6.5% | +0.162 |
| Josiah Ragsdale | 2026-05-30 | 42 | DOWNTREND | +4.4% | +6.2% | -0.129 |
| Josiah Ragsdale | 2026-06-28 | 60 | UPTREND | -8.9% | -3.0% | +0.291 |
| Josiah Ragsdale | 2026-09-11 | 114 | UPTREND | -16.7% | +3.0% | +0.029 |
| Johanfran Garcia | 2026-06-03 | 28 | DOWNTREND | +1.2% | -1.7% | -0.062 |
| Johanfran Garcia | 2026-07-30 | 56 | DOWNTREND | +2.0% | -2.9% | -0.091 |
| Johanfran Garcia | 2026-09-06 | 77 | UPTREND | -11.2% | +12.2% | +0.015 |
| Handelfry Encarnacion | 2026-05-06 | 28 | UPTREND | -5.1% | -0.2% | +0.177 |
| Handelfry Encarnacion | 2026-06-02 | 49 | DOWNTREND | +0.5% | -2.5% | -0.240 |
| Handelfry Encarnacion | 2026-06-27 | 70 | UPTREND | -6.9% | -3.6% | +0.156 |
| Handelfry Encarnacion | 2026-07-21 | 84 | DOWNTREND | +6.5% | +1.8% | -0.060 |
| Handelfry Encarnacion | 2026-08-18 | 105 | UPTREND | -8.9% | -3.0% | +0.065 |
| Jaison Chourio | 2026-06-21 | 50 | UPTREND | +0.0% | +4.8% | +0.066 |
| Jaison Chourio | 2026-06-30 | 57 | DOWNTREND | +8.0% | -0.2% | -0.337 |
| Jaison Chourio | 2026-09-13 | 115 | UPTREND | -11.3% | -2.8% | +0.079 |
| Andrew Fischer | 2026-05-10 | 28 | DOWNTREND | +2.9% | -4.2% | +0.360 |
| Andrew Fischer | 2026-05-29 | 42 | UPTREND | -11.0% | +14.8% | -0.168 |
| Andrew Fischer | 2026-06-13 | 54 | DOWNTREND | +8.9% | +10.3% | -0.058 |
| Andrew Fischer | 2026-07-31 | 89 | DOWNTREND | -2.2% | -11.0% | -0.107 |
| Andrew Fischer | 2026-09-03 | 117 | DOWNTREND | +3.6% | -7.6% | +0.233 |
| Andrew Fischer | 2026-09-11 | 124 | UPTREND | -6.7% | +19.9% | +0.366 |
| Starlyn Caba | 2026-06-24 | 42 | UPTREND | +3.4% | +5.0% | +0.075 |
| Starlyn Caba | 2026-07-17 | 56 | DOWNTREND | -1.9% | -3.5% | -0.110 |
| Starlyn Caba | 2026-08-08 | 70 | DOWNTREND | +8.4% | -5.0% | +0.059 |
| Starlyn Caba | 2026-08-19 | 77 | UPTREND | +1.6% | +3.2% | +0.113 |
| Zach Ehrhard | 2026-05-23 | 42 | UPTREND | -4.6% | +15.2% | +0.114 |
| Zach Ehrhard | 2026-06-17 | 63 | DOWNTREND | +10.9% | -3.8% | +0.277 |
| Zach Ehrhard | 2026-07-04 | 77 | DOWNTREND | -1.6% | -3.4% | -0.303 |
| Zach Ehrhard | 2026-08-05 | 98 | UPTREND | -4.5% | +3.3% | -0.097 |
| Zach Ehrhard | 2026-08-28 | 119 | DOWNTREND | +8.7% | -3.8% | -0.118 |
| Zach Ehrhard | 2026-09-20 | 138 | UPTREND | -13.5% | +2.7% | +0.010 |
| Cristofer Torin | 2026-05-23 | 35 | UPTREND | -12.8% | -5.4% | +0.061 |
| Cristofer Torin | 2026-06-11 | 49 | DOWNTREND | +2.8% | +2.8% | -0.098 |
| Cristofer Torin | 2026-06-19 | 56 | UPTREND | -4.7% | +4.3% | -0.072 |
| Cristofer Torin | 2026-06-28 | 63 | DOWNTREND | +3.1% | -4.4% | +0.075 |
| Cristofer Torin | 2026-08-18 | 98 | UPTREND | -3.5% | -5.1% | +0.101 |
| Cristofer Torin | 2026-09-13 | 118 | UPTREND | -3.9% | +5.2% | +0.006 |
| Aroon Escobar | 2026-05-07 | 28 | UPTREND | -13.8% | +3.5% | +0.045 |
| Aroon Escobar | 2026-05-15 | 35 | DOWNTREND | +6.1% | -9.1% | +0.087 |
| Aroon Escobar | 2026-06-07 | 56 | UPTREND | -12.4% | +11.4% | +0.020 |
| Aroon Escobar | 2026-07-02 | 77 | UPTREND | -1.7% | +9.5% | +0.094 |
| Aroon Escobar | 2026-07-24 | 91 | DOWNTREND | +12.0% | -12.7% | -0.113 |
| Aroon Escobar | 2026-08-11 | 105 | UPTREND | -8.5% | +1.7% | +0.160 |
| Aroon Escobar | 2026-09-13 | 132 | UPTREND | -3.5% | -5.3% | +0.093 |

A sudden jump may still be sampling noise or reflect unmodeled opponents, ballparks, fatigue or injuries. The historical timeline does not establish future breakout odds or cheap card prices.

**Interpretation:** A big 14-game move with no 28-game support is a possible fluke. Agreement across longer windows strengthens the evidence but does not prove the player's true future talent, exclude different opponents/parks, or predict the card market.


## Card identity watchlist — not buy prices

The public feed supplied some grossly inconsistent catalog estimates. They are retained in the machine-readable audit record, NOT shown as actionable prices.

| Player | Identified reference | Advertised all-in | Low-entry status | Catalog mark | Verified same-card sales | Decision |
|---|---|---:|---|---|---:|---|
| Cristofer Torin | 2023 Bowman Chrome Sapphire Edition Prospects #204 (PSA 10) | unknown | FIRST BOWMAN PACK AUTO NOT VERIFIED | **UNVERIFIED — HIDDEN** | — | PRICE GUIDE ONLY (NOT VERIFIED BUY) (missing or low deal score; missing or low breakout score; card-collector hype NOT verified; search ratio is not proof of quiet demand; price trend missing; Low-entry 1st Bowman auto not verified: FIRST_BOWMAN_PACK_AUTO_NOT_VERIFIED; no five independently title-matched recent sales of this EXACT card/grade; verified independent same-card sold comps unavailable) |
| Aroon Escobar | 2025 Bowman Chrome Prospects #BCP65 (PSA 9) | unknown | FIRST BOWMAN PACK AUTO NOT VERIFIED | **UNVERIFIED — HIDDEN** | — | PRICE GUIDE ONLY (NOT VERIFIED BUY) (missing or low deal score; missing or low breakout score; card-collector hype NOT verified; search ratio is not proof of quiet demand; price trend missing; Low-entry 1st Bowman auto not verified: FIRST_BOWMAN_PACK_AUTO_NOT_VERIFIED; no five independently title-matched recent sales of this EXACT card/grade; verified independent same-card sold comps unavailable) |

## Player skill-change explanations

- **Sebastian Dos Santos:** A, age 18: 14v14 K% 27.9%→15.9%, BB% 18.0%→20.6%, ISO 0.163→0.400; Only the short horizon is testable; NOT yet confirmed. Up to 28 same-team games assessed. Last game 2026-09-06. Collector interest and card price NOT validated.
- **Luis Escudero:** A, age 20: 14v14 K% 20.8%→9.3%, BB% 17.0%→18.5%, ISO 0.140→0.262; Only the short horizon is testable; NOT yet confirmed. Up to 28 same-team games assessed. Last game 2026-09-06. Collector interest and card price NOT validated.
- **Josiah Ragsdale:** AA, age 22: 14v14 K% 30.3%→21.2%, BB% 12.1%→13.6%, ISO 0.161→0.148; Only the short horizon is testable; NOT yet confirmed. Up to 28 same-team games assessed. Last game 2026-09-13. Collector interest and card price NOT validated.
- **Johanfran Garcia:** AA, age 21: 14v14 K% 40.4%→29.7%, BB% 7.0%→12.5%, ISO 0.157→0.273; Recent improvement is NOT confirmed by the 28-game comparison. Up to 56 same-team games assessed. Last game 2026-09-12. Collector interest and card price NOT validated.
- **Handelfry Encarnacion:** A, age 19: 14v14 K% 20.0%→7.4%, BB% 13.8%→11.8%, ISO 0.018→0.190; Recent improvement is NOT confirmed by the 28-game comparison. Up to 84 same-team games assessed. Last game 2026-08-28. Collector interest and card price NOT validated.
- **Jaison Chourio:** AA, age 21: 14v14 K% 26.1%→14.8%, BB% 15.9%→13.1%, ISO 0.018→0.096; Longer-window evidence conflicts with a shorter improvement. Up to 84 same-team games assessed. Last game 2026-09-13. Collector interest and card price NOT validated.
- **Andrew Fischer:** AA, age 22: 14v14 K% 37.5%→28.1%, BB% 5.4%→31.2%, ISO 0.440→0.419; Recent improvement is NOT confirmed by the 28-game comparison. Up to 56 same-team games assessed. Last game 2026-09-13. Collector interest and card price NOT validated.
- **Starlyn Caba:** A+, age 20: 14v14 K% 30.6%→25.0%, BB% 17.7%→21.7%, ISO 0.080→0.213; Recent improvement is NOT confirmed by the 28-game comparison. Up to 56 same-team games assessed. Last game 2026-08-25. Collector interest and card price NOT validated.
- **Zach Ehrhard:** AAA, age 23: 14v14 K% 30.2%→16.7%, BB% 7.9%→10.6%, ISO 0.143→0.153; Recent improvement is NOT confirmed by the 28-game comparison. Up to 84 same-team games assessed. Last game 2026-09-20. Collector interest and card price NOT validated.
- **Cristofer Torin:** AA, age 21: 14v14 K% 12.3%→8.5%, BB% 4.6%→9.9%, ISO 0.200→0.206; Recent improvement is NOT confirmed by the 28-game comparison. Up to 84 same-team games assessed. Last game 2026-09-13. Collector interest and card price NOT validated.
- **Aroon Escobar:** AA, age 21: 14v14 K% 17.5%→14.0%, BB% 14.0%→8.8%, ISO 0.167→0.260; Recent improvement is NOT confirmed by the 28-game comparison. Up to 84 same-team games assessed. Last game 2026-09-13. Collector interest and card price NOT validated.

**Why it isn't a buy:** the bot has measured early MiLB skill changes, but cannot yet verify card-specific collector attention and an affordable active purchase price. No fabricated trades.

---
Not a guarantee of profits. No catalog guide value is a real offer. Scores are NOT probabilities. Card-collector interest is NOT measured. No NBA/NFL discovery in this version.
