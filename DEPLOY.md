# Deploying the API

This puts `GET /api/sleepers` on a public URL so your frontend isn't tied to
your laptop. It's a plain Python stdlib server — no database, no framework.

## The one thing to decide first: card prices

Everything except eBay prices works from any server (Statcast, Google Trends,
prospects). **eBay blocks scraping from data-center IPs**, so on a deployed host
you have three choices for the price step:

| Option | How | Result |
|---|---|---|
| **eBay API token** (best) | set `EBAY_OAUTH_TOKEN` | real prices, un-blockable |
| **Residential proxy** | set `EBAY_PROXY_URL` (e.g. a rotating/residential proxy) | real prices via scrape |
| **Nothing** | — | prices come back `n/a`; scores/hype/ages still work |

The server auto-detects: token → official API; else proxy → scrape via proxy;
else plain scrape (which will 403 on most hosts). You can deploy first with
nothing and add a token later — the frontend keeps working either way.

> Getting an eBay token: create a free app at developer.ebay.com, request the
> `buy.marketplace.insights` scope (needs approval), and generate an OAuth
> application token. Until approved, run price checks from home or use a proxy.

## Environment variables

| Var | Needed? | What it does |
|---|---|---|
| `PORT` | auto (host sets it) | port the server binds to |
| `EBAY_OAUTH_TOKEN` | optional | official eBay price data |
| `EBAY_PROXY_URL` | optional | scrape eBay through this proxy instead |

## Option A — Render (easiest, has a free tier)

1. Push this repo to GitHub (already done).
2. On render.com → **New → Web Service** → connect the repo.
3. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python -m prehype serve --port $PORT`
4. (Optional) Add env var `EBAY_OAUTH_TOKEN`.
5. Deploy. You'll get a URL like `https://sleeper-board.onrender.com`.
6. Test: open `https://<your-url>/api/sleepers?demo=1`.

Render also auto-detects the included **Procfile**, so the start command is
optional.

## Option B — Railway / Fly.io / any Docker host

A **Dockerfile** is included, so:

- **Railway:** New Project → Deploy from repo. It builds the Dockerfile and
  injects `$PORT` automatically.
- **Fly.io:** `fly launch` (it detects the Dockerfile) → `fly deploy`.
- **Any host:**
  ```bash
  docker build -t sleeper-board .
  docker run -p 8000:8000 -e EBAY_OAUTH_TOKEN=xxxx sleeper-board
  ```

## After it's live: point the frontend at it

In your app-builder frontend, change the API base URL from
`http://localhost:8000` to your deployed URL. CORS is already open, so no other
change is needed. Keep `?demo=1` handy for offline UI work.

## A note on the live scan being slow

The live endpoint runs Statcast + Google Trends + eBay on each cold request
(cached for an hour after). On a free tier that can take 30–60s and the instance
may sleep when idle. If that's annoying, the natural upgrade is a **scheduled
refresh** (run the scan on a timer, serve the cached result instantly) — say the
word and I'll add it.
