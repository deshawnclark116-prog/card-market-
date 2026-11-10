# Card Bot — Daily Scouting Board

**Last scan:** 2026-11-10 | **Status:** EARLY_SKILL_WATCHLIST_OFFSEASON_NO_BUYS

**Paper-only experiment:** unverified catalog dollar values are HIDDEN. A verified same-card sale median is NOT an active offer. A player skill-change score is NOT an investment score.

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
- Comparison periods: **14v14, 28v28, 42v42** (up to 84 games of history); longer periods are overlapping diagnostics, not independent trials
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

| Evidence rank | Player | Level | Age | Persistence tier | Heuristic score | Last game | Collector interest |
|---:|---|---|---:|---|---:|---|---|
| 1 | Sebastian Dos Santos | A | 18 | EARLY — not confirmed | 62.8 | 2026-09-06 | **NOT VERIFIED** |
| 2 | Luis Escudero | A | 20 | EARLY — not confirmed | 54.2 | 2026-09-06 | **NOT VERIFIED** |
| 3 | Josiah Ragsdale | AA | 22 | EARLY — not confirmed | 43.3 | 2026-09-13 | **NOT VERIFIED** |
| 4 | Johanfran Garcia | AA | 21 | SHORT SPIKE — not confirmed | 45.8 | 2026-09-12 | **NOT VERIFIED** |
| 5 | Handelfry Encarnacion | A | 19 | SHORT SPIKE — not confirmed | 42.4 | 2026-08-28 | **NOT VERIFIED** |
| 6 | Jaison Chourio | AA | 21 | LONG WINDOW CONFLICT | 39.7 | 2026-09-13 | **NOT VERIFIED** |
| 7 | Andrew Fischer | AA | 22 | SHORT SPIKE — not confirmed | 38.6 | 2026-09-13 | **NOT VERIFIED** |
| 8 | Starlyn Caba | A+ | 20 | SHORT SPIKE — not confirmed | 38.2 | 2026-08-25 | **NOT VERIFIED** |
| 9 | Zach Ehrhard | AAA | 23 | SHORT SPIKE — not confirmed | 35.0 | 2026-09-20 | **NOT VERIFIED** |
| 10 | Cristofer Torin | AA | 21 | SHORT SPIKE — not confirmed | 28.8 | 2026-09-13 | **NOT VERIFIED** |
| 11 | Aroon Escobar | AA | 21 | SHORT SPIKE — not confirmed | 25.2 | 2026-09-13 | **NOT VERIFIED** |

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

**Interpretation:** A big 14-game move with no 28-game support is a possible fluke. Agreement across longer windows strengthens the evidence but does not prove the player's true future talent, exclude different opponents/parks, or predict the card market.


## Card identity watchlist — not buy prices

The public feed supplied some grossly inconsistent catalog estimates. They are retained in the machine-readable audit record, NOT shown as actionable prices.

| Player | Identified card and grade | Catalog price | Verified matching sale median | Verified sales | Status | Why not a buy |
|---|---|---|---:|---:|---|---|
| Cristofer Torin | 2023 Bowman Chrome Sapphire Edition Prospects #204 (PSA 10) | **UNVERIFIED — HIDDEN** | unknown | — | PRICE GUIDE ONLY (NOT VERIFIED BUY) | missing or low deal score; missing or low breakout score; card-collector hype NOT measured; search ratio is not proof of quiet demand; price trend missing; no 5 independently title-matched recent sales of this EXACT card/grade |
| Aroon Escobar | 2025 Bowman Chrome Prospects #BCP65 (PSA 9) | **UNVERIFIED — HIDDEN** | unknown | — | PRICE GUIDE ONLY (NOT VERIFIED BUY) | missing or low deal score; missing or low breakout score; card-collector hype NOT measured; search ratio is not proof of quiet demand; price trend missing; no 5 independently title-matched recent sales of this EXACT card/grade |

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
