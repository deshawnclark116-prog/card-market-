# Quick start — get your sleeper list

Run this on your own **laptop or desktop** (home internet). It won't fully work
on a cloud/work server because eBay blocks those for price data.

## One-time setup (about 2 minutes)

1. **Install Python** (if you don't have it): https://www.python.org/downloads/
   — grab version 3.10 or newer.

2. **Download this project** and open a terminal in its folder.

3. **Install the one add-on** it needs:
   ```
   pip install -r requirements.txt
   ```

## Run it

```
python run_sleepers.py
```

That's it. It will:
1. Find hitters who are quietly getting good (Baseball Savant)
2. Drop the ones people already hype (Google Trends)
3. Check what their cards actually cost (eBay)

…and print your list, like:

```
 1. Kyle Karros           sleeper   60/100 | age 24 | 2% hype | cards ~$18
    age 24, xwOBA jumped 0.258 -> 0.340 (+0.082) vs last year — leveled up ...
```

**How to read it:** high sleeper score + young + low hype + cheap cards = buy early.

## Handy options

```
python run_sleepers.py --top 15          # show more players
python run_sleepers.py --min-pa 150      # include part-time / newer players
python run_sleepers.py --no-prices       # skip eBay (faster, no price check)
```

## If something doesn't work

- **No eBay prices?** You're probably on a work/cloud network — try home wifi.
  The list still works, just without the price column.
- **No hype percentages?** Google Trends occasionally rate-limits. Wait a few
  minutes and rerun, or add `--no-prices` to go faster.
- **"python not found"?** Try `python3` instead of `python`.
