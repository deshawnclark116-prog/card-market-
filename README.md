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
# Runs fully offline on built-in demo players:
python -m prehype scan

# Only the ahead-of-the-crowd plays:
python -m prehype scan --only-early

# Live MLB fundamentals (free, no API key needed):
python -m prehype scan --sources mlb --only-early

# Tune what "dirt cheap" means for your reference card/grade:
python -m prehype scan --cheap-ref 20 --rich-ref 400
```

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
tests/
  test_scoring.py      # the strategy encoded as assertions
```

Adding a data source is the whole game — implement `DataSource.candidates()`
and return `Candidate`s with the three series filled in. The scorer doesn't
care where the numbers came from.

## Roadmap — turning the demo into a real edge

The scoring engine is done; the value now is in **real data feeds**:

- **Attention (the key early signal):** wire *sales velocity* (comps sold this
  week vs last), Google Trends (`pytrends`), and social mention counts. This is
  what fires before price.
- **Price:** eBay sold comps / 130point / Card Ladder-style series for real
  price momentum and cheapness.
- **Performance beyond MLB:** NBA/NFL stats, minor-league & prospect boards,
  expected-stats, role/opportunity changes (snaps, PAs, minutes).
- **Delivery:** a daily scheduled scan that pushes the `EARLY` list to your
  phone, so the system truly "does all the work."
- **Backtesting:** replay historical data to validate that `EARLY` calls
  actually preceded price runs, and auto-tune the weights.

Contributions to `sources/` are where this goes from a framework to money.

## Disclaimer

This is a research/decision-support tool, not financial advice. Card markets
are volatile and illiquid; do your own diligence and only risk what you can
afford to lose.
