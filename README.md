# prehype — get ahead of the sports card market

A system that does the scanning for you and surfaces the cards worth buying
**before** the crowd shows up:

> 🔥 *Jalen Rooke (MLB) — EARLY — dirt cheap, hype hasn't hit, breakout building*

The goal is simple: **be way ahead of the crowd.** Buy players whose
fundamentals point to a breakout while their cards are still cheap and quiet —
then sell into the hype once everyone else catches on.

## The thesis

Price is the *last* thing to move. The chain is almost always:

```
on-field performance / news  ->  attention (search, social, sales velocity)  ->  price
        (leading)                        (coincident)                            (lagging)
```

The edge isn't predicting the future — it's spotting cards where the first two
signals are already firing but **price is still asleep.** That gap is the
opportunity window. Once price starts running, you're late.

## Prospects (minor leagues) — where Bowman 1st autos live

```bash
python -m prehype prospects --min-pa 150            # scan the minors
python -m prehype prospects --min-pa 150 --with-prices
```

Bowman 1st autos are *prospect* cards, so the real edge is in the minors. The
minors have no Statcast, so the leading signal is **age-relative-to-level** (a
20-year-old holding his own in Double-A is a screaming buy), plus OPS and plate
discipline (walk/strikeout rates travel up levels). Same downstream funnel:
hype meter + Bowman 1st auto price + price-momentum gate. See `sources/milb.py`
and `find_prospects()`.

Note: this ranks by *numbers*, not scouting reports — so a toolsy, highly-ranked
name with a merely-good statline lands mid-pack, while a lesser-known kid with a
loud season rises. That's the point (be early on the numbers), but it means the
tool complements prospect lists, it doesn't replace scouting.

## Player-first, not price-first

There are far fewer players about to break out than there are cheap cards, so
we start with the small pile:

```
ALL hitters --> who's about to break out? --> (top few) --> check card price --> "cheap + hot = BUY"
                (Statcast leading signal)                   (eBay, only now)
```

Covers **both hitters and pitchers**. For a pitcher the signal is flipped: it's
xwOBA-*against* (how hard batters hit him), so a breakout is a *drop* — he got
nastier while his ERA/name hasn't caught up. Scan `--type both` (default),
`--type batter`, or `--type pitcher`.

Pitchers are limited to **starters** by default (relievers' cards carry little
value) and held to a higher batters-faced floor so small samples don't top the
list — pass `--include-relievers` to keep them.

### Which cards it prices

The eBay step prices the prospect cards that actually carry upside — **Bowman
Chrome 1st autos** and **rookie autos** — not base rookies. Each candidate shows
both. Configure in `breakouts.py` (`CARD_QUERY_BUILDERS` / `DEFAULT_CARDS`).

The breakout signal scores **improvement, not level** — this is the important
part. Ranking hitters by skill just lists the stars (already famous, cards
expensive, no edge). A real sleeper is someone who was average/unknown and
quietly *leveled up*. So the score rewards:

* the **jump in quality of contact** (expected wOBA) vs last year,
* **gated** so it only counts if the player wasn't already a star,
* a **youth boost** (young cards have the most upside),
* new faces with strong contact as "emerging."

Established stars score low here on purpose: their year-over-year jump is ~zero
and their prior level was already elite, so the "was under the radar" gate
zeroes them out. See `sources/savant.py` and `breakouts.py`.

### The hype meter (what makes a sleeper a sleeper)

Improvement alone still surfaces *hyped* young studs — the toolsy prospects
scouts and collectors already found (Elly De La Cruz, Pete Crow-Armstrong).
Their cards are expensive; no edge. "Sleeper" is a **price/attention** fact, not
a stats fact.

So the breakout scan re-ranks by **Google Trends search interest**
(`sources/trends.py`): a live "how hyped is he already" meter. Every player is
measured as a percent of a famous anchor's search volume, then:

```
sleeper score = breakout score  ×  (1 − how-hyped-he-already-is)
```

A famous name with lots of searches gets crushed; an unknown who's quietly
leveling up keeps almost all his score. This runs by default on the breakout
shortlist (`--no-hype` to skip). Needs `pytrends` (`pip install pytrends`);
degrades gracefully without it.

### The price-momentum gate (don't buy what already ran)

Google Trends measures the *general public*, but card collectors are a niche —
a card can already be climbing while search interest stays quiet. So the eBay
step also checks each card's **price trend**: flat or falling = still asleep
(good); already up ~30%+ = you're probably late. This produces the final
**deal score**:

```
deal score = sleeper score  ×  (card price still asleep?)
```

Two identical sleepers with identical hype now separate correctly: the one
whose Bowman 1st auto is flat keeps its score; the one already up 50%+ collapses
toward zero and gets flagged LATE. See `price_momentum_from_comps` and
`add_prices`.

Because the price check runs only on the breakout shortlist, it's a few eBay
lookups instead of thousands — which also sidesteps most of eBay's IP blocking.

## The Pre-Hype Score

Every player gets a single 0–100 score built from transparent parts:

| Component | What it measures | We want |
|---|---|---|
| **Performance level & momentum** | Are the fundamentals strong and *rising*? | High (this is the breakout gate) |
| **Cheapness** | How much room is left to run? | High (dirt cheap) |
| **Price asleep** | Has price *not* moved yet? | High |
| **Under the radar** | Has the crowd noticed? | Low attention |
| **Risk** | Injury, age, already-late | Low |

Rules that make it trustworthy:

1. **Breakout is a gate, not a bonus.** No rising fundamentals → the score
   collapses. Cheap-and-going-nowhere is a value trap, not an opportunity.
2. **Being early is rewarded; being late is penalized.** Rising price and
   rising attention *lower* the score — the window is closing.
3. **No black box.** Every score ships with its component breakdown and
   plain-English reasons before you spend a dollar.

Verdicts you'll see: `EARLY` 🔥 · `WATCH` 👀 · `WINDOW_CLOSING` ⏳ ·
`TOO_LATE` 🚪 · `PASS` 💤.

## Quick start

```bash
# PLAYER-FIRST: find MLB hitters about to break out (real Statcast data),
# then check their card prices for just the shortlist:
python -m prehype breakouts --min-pa 300
python -m prehype breakouts --min-pa 300 --with-prices   # adds eBay price check

# Runs fully offline on built-in demo players:
python -m prehype scan

# Only the ahead-of-the-crowd plays:
python -m prehype scan --only-early

# Live MLB fundamentals (free, no API key needed):
python -m prehype scan --sources mlb --only-early

# Only show players whose card is actually cheap (a hard cap):
python -m prehype breakouts --max-price 25
python -m prehype prospects --max-price 20   # cheap Bowman 1st autos only

# Real eBay sold comps for your watchlist (price + sales velocity):
cp watchlist.example.json watchlist.json   # then edit it
python -m prehype scan --sources ebay --only-early

# Tune what "dirt cheap" means for your reference card/grade:
python -m prehype scan --cheap-ref 20 --rich-ref 400
```

Run the JSON API (for a web frontend):

```bash
python -m prehype serve
# GET http://localhost:8000/api/sleepers          (live scan)
# GET http://localhost:8000/api/sleepers?demo=1   (instant sample data)
```

Returns a ranked JSON array (name, position, age, dealScore, breakoutScore,
hypePct, reason, priceTrend, priceStatus, and Bowman-1st/rookie-auto card
prices). CORS is open so a frontend on any origin can call it; results are
cached in memory. Point an app-builder frontend at `?demo=1` while building the
UI, then switch to the live endpoint. Run it on a home/residential IP (or with
an eBay API token) so the price fields populate.

Deploy it so the frontend isn't tied to your laptop: see **[DEPLOY.md](DEPLOY.md)**
(Render / Railway / Fly / Docker; includes the eBay-token vs proxy note). The
server honors `$PORT`; a `Procfile` and `Dockerfile` are included.

Run the tests:

```bash
python -m pytest -q
```

## How it's wired

```
prehype/
  models.py            # Candidate + three signal series + Signal output
  scoring.py           # the Pre-Hype Score engine (the moat)
  pipeline.py          # gather -> score -> rank -> filter
  cli.py               # `python -m prehype scan`
  sources/
    base.py            # DataSource interface — plug in any feed
    demo.py            # synthetic players so it runs offline
    mlb.py             # real, free MLB StatsAPI performance feed
    ebay.py            # real eBay sold comps -> price + sales-velocity signals
    watchlist.py       # score your own cards, priced by eBay comps
tests/
  test_scoring.py      # the strategy encoded as assertions
  test_ebay.py         # eBay parsing verified against a saved HTML fixture
```

## eBay sold comps — the price + early-attention signal

`sources/ebay.py` turns eBay sold/completed listings into two real signals:

- **Price** — weekly median sold price → price momentum + cheapness.
- **Sales velocity** — weekly sold *count* → attention. Velocity spikes
  *before* price, so this is the earliest crowd signal we have.

You drive it with a small `watchlist.json` (see `watchlist.example.json`):
each player gets an `ebay_query` that isolates their reference card/grade, and
an optional hand-entered `performance` series until a real fundamentals feed is
wired for that sport.

**Two backends, because eBay blocks scrapers from cloud/datacenter IPs (403):**

| Backend | When to use | Notes |
|---|---|---|
| `ScrapeBackend` (default) | Running from your own machine / residential IP, or via a scraping proxy (`proxy_url=`) | Parses eBay HTML. Fails gracefully to `[]` on a blocked IP. |
| `MarketplaceInsightsBackend` | Anywhere, including servers | eBay's official sold-comps API. Set `EBAY_OAUTH_TOKEN` (needs eBay approval for the `buy.marketplace.insights` scope). No IP blocking. |

Comps are cached to `~/.cache/prehype/ebay` (6h TTL) and passed through
`trim_price_outliers()` so one mispriced variant (an auto/refractor caught by a
loose query) doesn't wreck the median. **Tighten your `ebay_query` first**;
trimming is the safety net.

Adding a data source is the whole game — implement `DataSource.candidates()`
and return `Candidate`s with the three series filled in. The scorer doesn't
care where the numbers came from.

## Roadmap — turning the demo into a real edge

The scoring engine is done; the value now is in **real data feeds**:

- ✅ **Price (eBay sold comps):** done — `sources/ebay.py`, weekly median with
  outlier trimming.
- ✅ **Attention via eBay sales velocity:** done — weekly sold counts. Can still
  be enriched with Google Trends (`pytrends`) and social mention counts.
- **Performance beyond MLB:** NBA/NFL stats, minor-league & prospect boards,
  expected-stats, role/opportunity changes (snaps, PAs, minutes). This is the
  biggest remaining gap — the breakout gate needs real fundamentals per sport.
- **Delivery:** a daily scheduled scan that pushes the `EARLY` list to your
  phone, so the system truly "does all the work."
- **Backtesting:** replay historical data to validate that `EARLY` calls
  actually preceded price runs, and auto-tune the weights.

Contributions to `sources/` are where this goes from a framework to money.

## Disclaimer

This is a research/decision-support tool, not financial advice. Card markets
are volatile and illiquid; do your own diligence and only risk what you can
afford to lose.
