"""2027 prep draft radar: public rosters + observed showcase fastball data.

Source-only: no subscriptions, search-ranking-driven discovery, invented exit velo,
or grade assumptions. This is a *pre-card research board*, not a price board.

Public tournament roster grade is the minimum eligibility proof. Tournament
pitching velocity is a single event MAXIMUM, not average, pitch quality, or
projected stuff. Even positive deltas are exploratory and never 'breakout'.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

DRAFT_CLASS = 2027
USA_ROSTER = "https://www.usabaseball.com/team/18u/roster"
# Official USA Baseball news archive dates final 2026 18U roster Aug 26.
USA_ROSTER_PUBLISHED = date(2026,8,26)
PG_GLOBAL_PUBLIC_EVENT_RECORDS = "https://www.perfectgame.org/Records/statrankings.aspx"
# Unauthenticated publicly rendered roster and FB-velocity tables.
# Do NOT request Perfect Game DiamondKast game statistics or login pages.
EVENTS = (
    {
        "id": "pg_2026_17u_wwba",
        "label": "2026 PG 17U WWBA National Championship",
        "date": "2026-06-30",
        "roster": "https://www.perfectgame.org/Events/Rosters.aspx?event=141563",
        "velocities": "https://www.perfectgame.org/Events/velocities/default.aspx?event=141563",
    },
    {
        "id": "pg_2026_wwba_jupiter",
        "label": "2026 PG WWBA World Championship",
        "date": "2026-10-12",
        "roster": "https://www.perfectgame.org/Events/Rosters.aspx?event=139793",
        "velocities": "https://www.perfectgame.org/Events/velocities/default.aspx?event=139793",
    },
)
OUTPUT_JSON = "data/card_bot_hs_draft_2027_latest.json"
OUTPUT_MD = "HS_DRAFT_2027_BOARD.md"
USER_AGENT = "Card-Bot-2027-Draft-Research/1.0"
MAX_PAGE_BYTES = 3_000_000
MIN_VELO_DELTA_MPH = 3


def clean(s):
    return " ".join(str(s or "").replace("\xa0"," ").split())


def key(name):
    s=unicodedata.normalize("NFKD",clean(name)).lower()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9 ]","", "".join(
        ch for ch in s if not unicodedata.combining(ch)))).strip()


class Tables(HTMLParser):
    """Extract only plain text from public HTML tables with no JS execution."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables=[]
        self.depth=0
        self.table=None
        self.row=None
        self.cell=None

    def handle_starttag(self,tag,attrs):
        if tag=="table":
            self.depth+=1
            if self.depth==1:
                self.table=[]
        elif self.depth==1 and tag=="tr":
            self.row=[]
        elif self.depth==1 and tag in ("td","th") and self.row is not None:
            self.cell=[]

    def handle_data(self,data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self,tag):
        if tag in ("td","th") and self.depth==1 and self.cell is not None:
            self.row.append(clean("".join(self.cell)))
            self.cell=None
        elif tag=="tr" and self.depth==1 and self.row is not None:
            if any(self.row):
                self.table.append(self.row)
            self.row=None
        elif tag=="table" and self.depth:
            if self.depth==1 and self.table:
                self.tables.append(self.table)
                self.table=None
            self.depth-=1


def parse_tables(html):
    parser=Tables()
    parser.feed(html)
    return parser.tables


def _row_mapping(table, fields):
    """Locate explicit table column names; reject unknown/changed schemas."""
    for i,headers in enumerate(table):
        h=[key(v) for v in headers]
        indices={}
        for logical,alternatives in fields.items():
            for alias in alternatives:
                if alias in h:
                    indices[logical]=h.index(alias)
                    break
        if len(indices)==len(fields):
            for row in table[i+1:]:
                if len(row)>max(indices.values()):
                    yield {k:clean(row[n]) for k,n in indices.items()}


def usa_18u_players(html):
    out=[]
    for table in parse_tables(html):
        for v in _row_mapping(table,{
            "name":("name",),
            "position":("position",),
            "grad":("class",),
        }):
            if v["grad"]!=str(DRAFT_CLASS):
                continue
            if not (2<=len(v["name"].split())<=5):
                continue
            out.append({"name":v["name"],"position":v["position"],
                        "graduation_year":DRAFT_CLASS,
                        "source":USA_ROSTER,
                        "source_kind":"USA_BASEBALL_18U_NATIONAL_TEAM",
                        "national_team_2026":True})
    return _unique(out)


def pg_event_roster(html, source):
    out=[]
    for table in parse_tables(html):
        for v in _row_mapping(table,{
            "name":("players","player"),
            "grad":("grad",),
            "position":("pos","position"),
        }):
            if v["grad"]!=str(DRAFT_CLASS):
                continue
            if not (2<=len(v["name"].split())<=5):
                continue
            out.append({"name":v["name"],"position":v["position"],
                        "graduation_year":DRAFT_CLASS,
                        "source":source,"source_kind":"PUBLIC_PG_EVENT_ROSTER",
                        "national_team_2026":False})
    return _unique(out)


def pg_event_velocities(html, event):
    out=[]
    for table in parse_tables(html):
        for v in _row_mapping(table,{
            "name":("players","player"),
            "mph":("fb",),
        }):
            try:
                mph=int(v["mph"])
            except (ValueError, TypeError):
                continue
            if not (55<=mph<=106) or not (2<=len(v["name"].split())<=5):
                continue
            out.append({
                "name":v["name"],"event_id":event["id"],
                "event":event["label"],"event_end":event["date"],
                "fastball_peak_mph":mph,"source":event["velocities"],
                "type":"EVENT_FASTBALL_PEAK_NOT_AVERAGE",
            })
    # Some PG rows show a pitcher under more than one team. Preserve only
    # the highest EVENT peak, not duplicate pseudo-independent evidence.
    best={}
    for r in out:
        n=key(r["name"])
        if n not in best or r["fastball_peak_mph"]>best[n]["fastball_peak_mph"]:
            best[n]=r
    return list(best.values())


def pg_public_global_event_velocities(html):
    """Match source-published FB numbers to events with verified dates.

    This public cross-event table is a top-velocity LEADERBOARD and its
    visibility is not a neutral/random sample. Never use it to choose
    athletes or label them as hidden; ONLY enrich grad-verified players.
    """
    found={}
    for table in parse_tables(html):
        for v in _row_mapping(table,{
            "name":("player","players"),
            "mph":("fb",),
            "event":("event",),
        }):
            event=next((e for e in EVENTS if key(v["event"])==key(e["label"])),None)
            if event is None:
                continue
            try:
                mph=int(v["mph"])
            except (TypeError,ValueError):
                continue
            if not (55<=mph<=106) or not (2<=len(v["name"].split())<=5):
                continue
            k=(key(v["name"]),event["id"])
            row={"name":v["name"],"event_id":event["id"],
                 "event":event["label"],"event_end":event["date"],
                 "fastball_peak_mph":mph,
                 "source":PG_GLOBAL_PUBLIC_EVENT_RECORDS,
                 "type":"TOP_PUBLIC_EVENT_FB_PEAK_LEADERBOARD_NOT_FULL_SAMPLE"}
            if k not in found or mph>found[k]["fastball_peak_mph"]:
                found[k]=row
    return list(found.values())


def _unique(players):
    rows={}
    for p in players:
        rows.setdefault(key(p["name"]),p)
    return list(rows.values())


def get_public_html(url,*,opener=None,timeout=14):
    allow=(
        url in (USA_ROSTER,PG_GLOBAL_PUBLIC_EVENT_RECORDS)
        or any(url in (e["roster"],e["velocities"]) for e in EVENTS)
    )
    if not allow:
        raise ValueError("Unapproved public source")
    opener=opener or urllib.request.urlopen
    try:
        req=urllib.request.Request(url,headers={
            "User-Agent": USER_AGENT,"Accept":"text/html",
        })
        with opener(req,timeout=timeout) as response:
            content=response.read(MAX_PAGE_BYTES+1)
        if len(content)>MAX_PAGE_BYTES:
            raise ValueError("Response exceeds approved source-size budget")
        return content.decode("utf-8","replace")
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        return None


def run_hs_scan(*,as_of=None,fetch=get_public_html):
    as_of=as_of or date.today()
    sources=[]
    qualifying={}
    event_peaks=defaultdict(list)
    event_roster_keys={}
    usa_is_public=as_of>=USA_ROSTER_PUBLISHED
    usa_html=fetch(USA_ROSTER) if usa_is_public else None
    usa=usa_18u_players(usa_html) if usa_html else []
    sources.append({"url":USA_ROSTER,"available":bool(usa_html),
                    "2027_players_extracted":len(usa),
                    "purpose":("Official high-exposure roster"
                               if usa_is_public else
                               "NOT YET PUBLIC AS OF THIS HISTORICAL DATE")})
    for p in usa:
        qualifying[key(p["name"])]={
            "name":p["name"],"graduation_year":DRAFT_CLASS,
            "position":p["position"],"source_roster_urls":[p["source"]],
            "national_team_2026":True,
        }
    for event in EVENTS:
        if date.fromisoformat(event["date"])>as_of:
            continue
        roster_html=fetch(event["roster"])
        roster=pg_event_roster(roster_html,event["roster"]) if roster_html else []
        event_verified_keys={key(p["name"]) for p in roster}
        event_roster_keys[event["id"]]=event_verified_keys
        usa_verified_keys={key(p["name"]) for p in usa}
        sources.append({"url":event["roster"],"available":bool(roster_html),
                        "2027_players_extracted":len(roster),
                        "purpose":"Public graduation-year eligibility"})
        for p in roster:
            k=key(p["name"])
            found=qualifying.setdefault(k,{
                "name":p["name"],"graduation_year":DRAFT_CLASS,
                "position":p["position"],"source_roster_urls":[],
                "national_team_2026":False,
            })
            if p["source"] not in found["source_roster_urls"]:
                found["source_roster_urls"].append(p["source"])
        velo_html=fetch(event["velocities"])
        velos=pg_event_velocities(velo_html,event) if velo_html else []
        sources.append({"url":event["velocities"],"available":bool(velo_html),
                        "raw_velocities_extracted":len(velos),
                        "purpose":"Public event-level measured max FB mph"})
        for v in velos:
            k=key(v["name"])
            # Reject apparent identity match without the correct class. The
            # velocity table alone has NO graduation-year column.
            if k in qualifying and (
                k in event_verified_keys or k in usa_verified_keys
            ):
                event_peaks[k].append(v)
    # Fallback for a publicly posted single-event velocity feed that
    # refuses to load, but ONLY for class-verified players. The global
    # list is highly selected and cannot provide 'normal' velocity.
    global_html=fetch(PG_GLOBAL_PUBLIC_EVENT_RECORDS)
    global_velos=pg_public_global_event_velocities(global_html) if global_html else []
    sources.append({"url":PG_GLOBAL_PUBLIC_EVENT_RECORDS,
                    "available":bool(global_html),
                    "raw_velocities_extracted":len(global_velos),
                    "purpose":"Public cross-event top FB speeds; TOP-ONLY BIAS"})
    usa_verified_keys={key(p["name"]) for p in usa}
    for v in global_velos:
        k=key(v["name"])
        if (v["event_end"]>as_of.isoformat() or k not in qualifying
                or not (k in usa_verified_keys or
                        k in event_roster_keys.get(v["event_id"],set()))):
            continue
        existing=[row for row in event_peaks[k] if row["event_id"]==v["event_id"]]
        if not existing:
            event_peaks[k].append(v)
        elif v["fastball_peak_mph"]>max(row["fastball_peak_mph"] for row in existing):
            event_peaks[k]=[row for row in event_peaks[k]
                            if row["event_id"]!=v["event_id"]]+[v]
    rows=[]
    for k,p in sorted(qualifying.items(),key=lambda x:x[1]["name"].casefold()):
        measurements=sorted(event_peaks[k],key=lambda v:(v["event_end"],v["event_id"]))
        # Strong event-level repeatability? No: one maxima per event, 2
        # observations at most. Never promote to an actual breakout finding.
        prior=measurements[-2] if len(measurements)>1 else None
        latest=measurements[-1] if measurements else None
        change=latest["fastball_peak_mph"]-prior["fastball_peak_mph"] if prior and latest else None
        if change is not None and change>=MIN_VELO_DELTA_MPH:
            status="OBSERVED_VELOCITY_INCREASE_NOT_CONFIRMED_BREAKOUT"
        elif change is not None and change<=-MIN_VELO_DELTA_MPH:
            status="OBSERVED_VELOCITY_DECLINE_NOT_CONFIRMED"
        elif change is not None:
            status="NO_LARGE_CHANGE_IN_EVENT_PEAK_VELOCITY"
        elif latest:
            status="SINGLE_EVENT_PEAK_NO_CHANGE_DETECTABLE"
        else:
            status="NO_PUBLIC_MEASUREMENT_AVAILABLE"
        rows.append({
            **p,
            "source_roster_urls":p["source_roster_urls"],
            "market_exposure":("NATIONAL_TEAM_PUBLICLY_RECOGNIZED"
                               if p["national_team_2026"] else
                               "COLLECTOR_HYPE_UNKNOWN"),
            "observations":measurements,
            "fastball_peak_change_mph":change,
            "measurement_status":status,
            "evidence_not_prediction":True,
            "draft_outcome":"NOT_EVALUATED_NO_SIGNING_PROJECTION",
            "bowman_first_auto_status":"NOT_VERIFIED_OR_NOT_YET_ISSUED",
            "card_buy_eligible":False,
        })
    # Inspect genuine observed changes first, not national-team fame.
    priority={"OBSERVED_VELOCITY_INCREASE_NOT_CONFIRMED_BREAKOUT":0,
              "SINGLE_EVENT_PEAK_NO_CHANGE_DETECTABLE":1,
              "NO_LARGE_CHANGE_IN_EVENT_PEAK_VELOCITY":2,
              "OBSERVED_VELOCITY_DECLINE_NOT_CONFIRMED":3,
              "NO_PUBLIC_MEASUREMENT_AVAILABLE":4}
    rows.sort(key=lambda x:(priority[x["measurement_status"]],
                            -((x["fastball_peak_change_mph"]) or 0),
                            x["name"]))
    return {
        "schema":"HS_PRE_DRAFT_RAW_EVENT_RADAR_V1",
        "draft_class":DRAFT_CLASS,
        "as_of":as_of.isoformat(),
        "source_diagnostics":sources,
        "players_with_verified_2027_graduation":len(rows),
        "public_event_velocity_measurements":sum(len(x["observations"]) for x in rows),
        "observed_velocity_increases":sum(
            x["measurement_status"]=="OBSERVED_VELOCITY_INCREASE_NOT_CONFIRMED_BREAKOUT"
            for x in rows),
        "confirmed_breakout_players":0,
        "verified_cheap_bowman_first_autos":0,
        "players":rows,
        "coverage_warning":(
            "Partial PUBLIC tournament-roster and event-max-velocity snapshots, "
            "not a comprehensive national high-school database. No free "
            "DiamondKast access, hitting game logs, pitching command, spin, "
            "or replicated pitch-quality evidence. Showcase and public "
            "top-velocity leaderboard selection bias against unknown players. "
            "A 3+ mph jump between event PEAKS may "
            "be noise, environment, measurement changes or small sample; "
            "it does NOT establish a future skill breakout. Event "
            "name joins are not verified persistent identities; no Bowman "
            "card market claims or purchase recommendations."),
    }


def render_markdown(result):
    lines=[
        "# Card Bot — 2027 High School Draft Watch",
        "",
        f"**Scan date:** {result['as_of']} | **Target class:** High-school graduation {result['draft_class']}",
        "",
        "## Why we are watching before the draft",
        "",
        "Our goal is to discover measurable player development **before the 2027 "
        "MLB Draft and first Bowman card release/repricing**. This is a "
        "**PRE-CARD RESEARCH** list, not a list of buyable Bowman 1st autos. "
        "Existing USA Baseball national-team selections are highly publicized "
        "and MUST NOT be described as undiscovered sleepers.",
        "",
        f"- Verified 2027-graduate roster entries in sampled public sources: **{result['players_with_verified_2027_graduation']}**",
        f"- Event-level velocity observations matched to these entries: **{result['public_event_velocity_measurements']}**",
        f"- Unconfirmed increases in public event peak velocity: **{result['observed_velocity_increases']}**",
        "- Confirmed future breakouts: **0** — no evidence supports such a claim.",
        "- Verified cheap 1st Bowman autos: **0** — not researched/available as an actionable card class.",
        "",
        "**Data limit:** " + result["coverage_warning"],"",
        "## Source access checks","",
        "| Public source | Available | Verified grad-2027 records or velocity observations | Purpose |",
        "|---|---|---:|---|",
    ]
    for s in result["source_diagnostics"]:
        lines.append(
            f"| [Source]({s['url']}) | {'yes' if s['available'] else 'NO — not verified'} | "
            f"{s.get('2027_players_extracted',s.get('raw_velocities_extracted',0))} | "
            f"{s['purpose']} |"
        )
    lines += [
        "",
        "## All class-2027 players in public roster samples",
        "",
        "Do not confuse a high raw fastball peak, being selected to Team USA, "
        "or a card being absent with market undervaluation.",
        "",
        "| Player | Grad | Position | 2026 USA 18U | Public max-FB event observations | Change | Status |",
        "|---|---:|---|---|---|---|---|",
    ]
    for p in result["players"]:
        observations="; ".join(
            f"[{e['event_end']}: {e['fastball_peak_mph']} mph]({e['source']})"
            for e in p["observations"]
        ) or "unavailable"
        change=(f"{p['fastball_peak_change_mph']:+d} mph"
                if p["fastball_peak_change_mph"] is not None else "—")
        lines.append(
            f"| {p['name']} | {p['graduation_year']} | {p['position']} | "
            f"{'YES — already prominent' if p['national_team_2026'] else 'no verification from source'} | "
            f"{observations} | {change} | {p['measurement_status'].replace('_',' ')} |"
        )
    lines += ["",
              "## Source and model integrity",
              "",
              "- The player list comes from **official public USA Baseball and publicly exposed tournament rosters**, not draft-prospect articles or rankings.",
              "- The event fastball values are **single reported event maxima** (not a real season or multiple-start velocity average).",
              "- A name on a velocity table without a confirmed grad year is **not** silently assigned to the 2027 draft class.",
              "- A high-school graduate may attend college instead of being drafted/signed. A grad year is an eligibility-screen input, not a draft-outcome forecast.",
              "- New live games and measured skills must establish repeated improvement before we classify a genuine breakout.",
              "- This job does **not** create paper-card purchases or alter the existing $100 ledger.",
              "",
              "## Parallel MiLB radar",
              "",
              "The 2026 full-season MiLB research stays available at "
              "[the scouting dashboard](CARD_BOT_DASHBOARD.md).",
              ""]
    return "\n".join(lines)


def write_hs_results(result,*,json_path=OUTPUT_JSON,md_path=OUTPUT_MD):
    for path,payload in ((json_path,json.dumps(result,indent=2,sort_keys=True)+"\n"),
                         (md_path,render_markdown(result)+"\n")):
        p=Path(path)
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(payload,encoding="utf-8")


def main(argv=None):
    parser=argparse.ArgumentParser(description="Anonymous 2027 HS draft scan, no purchases")
    parser.add_argument("--as-of",type=date.fromisoformat,default=date.today())
    args=parser.parse_args(argv)
    result=run_hs_scan(as_of=args.as_of)
    write_hs_results(result)
    print(json.dumps({
        "as_of":result["as_of"],
        "2027_graduates":result["players_with_verified_2027_graduation"],
        "measurements":result["public_event_velocity_measurements"],
        "unconfirmed_velocity_jumps":result["observed_velocity_increases"],
        "source_availability":[(s["url"],s["available"])
                               for s in result["source_diagnostics"]],
        "actual_buy_candidates":0,
    },sort_keys=True))


if __name__=="__main__":
    main()
