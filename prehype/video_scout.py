"""Daily video scouting evidence registry for prep + MiLB athlete lists.

The program only WATCHES clips when original authorized video bytes exist
and can be decoded. A roster URL, Google/YouTube link, or video article is
not evidence of visual analysis. No athlete or game footage is bundled.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path

from prehype.video_evidence import (
    MODEL_VERSION, analyze_local_video, allowed_clip_metadata,
    compare_same_camera_observations, fetch_verified_video,
    safe_video_url, trusted_hosts,
)

MANIFEST_PATH = "data/card_bot_video_manifest.json"
CACHE_PATH = "data/card_bot_video_clip_cache.json"
HS_INDEX_PATH = "data/card_bot_hs_draft_2027_latest.json"
MILB_INDEX_PATH = "data/card_bot_full_season_latest.json"
SCOUTING_INDEX_PATH = "data/card_bot_scouting_latest.json"
OUTPUT_JSON = "data/card_bot_video_scouting_latest.json"
OUTPUT_MD = "VIDEO_SCOUTING_BOARD.md"
MAX_NEW_CLIPS_PER_RUN = 6
MAX_CACHE_ENTRIES = 150


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return default


def athlete_index(hs, milb):
    verified={}
    for row in hs.get("players",[]):
        pid=str(row.get("player_id") or "")
        name=row.get("name")
        if pid.isdigit() and isinstance(name,str):
            verified[("HS_2027",pid)]=name
    for row in milb.get("players",[]):
        pid=str(row.get("player_id") or "")
        name=row.get("name")
        if pid.isdigit() and isinstance(name,str):
            verified[("MILB_2026",pid)]=name
    return verified


def athlete_queue(hs, milb, scout, observed):
    """Every source-verified player remains visible, not just card-buy picks."""
    improving={str(p["player_id"]):p for p in (
        (scout.get("discovery") or {}).get("all_skill_improvement_candidates") or []
    ) if p.get("player_id")}
    rows=[]
    for p in hs.get("players",[]):
        pid=str(p.get("player_id") or "")
        if not pid.isdigit():
            continue
        rows.append({
            "pool":"HS_2027", "player_id":pid, "name":p["name"],
            "baseball_evidence":"PRE_DRAFT_CLASS_VERIFIED_ROSTER_NOT_A_BREAKOUT",
            "existing_public_exposure":p.get("market_exposure","UNKNOWN"),
            "video_status":observed.get(("HS_2027",pid),"NO_APPROVED_FOOTAGE_ANALYZED"),
            "film_priority":"NEEDS_INDEPENDENT_GAME_FOOTAGE",
            "source":"data/card_bot_hs_draft_2027_latest.json",
        })
    for p in milb.get("players",[]):
        pid=str(p.get("player_id") or "")
        if not pid.isdigit():
            continue
        improved=improving.get(pid)
        rows.append({
            "pool":"MILB_2026", "player_id":pid, "name":p["name"],
            "baseball_evidence":(improved.get("evidence_tier")
                                 if improved else p.get("development_phase","UNCONFIRMED")),
            "existing_public_exposure":"TOP_100_OR_HOBBY_UNVERIFIED",
            "video_status":observed.get(("MILB_2026",pid),"NO_APPROVED_FOOTAGE_ANALYZED"),
            "film_priority":("STATISTICAL_CHANGE_REVIEW_FOOTAGE"
                             if improved else "LOWER_PRIORITY_RAW_SEASON_TRACKING"),
            "source":"data/card_bot_full_season_latest.json",
        })
    priority={"STATISTICAL_CHANGE_REVIEW_FOOTAGE":0,
              "NEEDS_INDEPENDENT_GAME_FOOTAGE":1,
              "LOWER_PRIORITY_RAW_SEASON_TRACKING":2}
    return sorted(rows,key=lambda r:(priority[r["film_priority"]],r["pool"],r["name"]))


def clip_fingerprint(row):
    # Any different crop, rep, reviewer, license, camera or video bytes
    # invalidates the prior observation and forces fresh analysis.
    return hashlib.sha256(json.dumps(
        {"model":MODEL_VERSION,"clip":row},
        sort_keys=True,ensure_ascii=True,
    ).encode("utf-8")).hexdigest()


def scan_video_evidence(manifest, hs, milb, scout, *, as_of=None,
                        allowed_hosts=None, cache=None,
                        fetch_video=fetch_verified_video,
                        analyze_video=analyze_local_video):
    as_of=as_of or date.today()
    hosts=trusted_hosts() if allowed_hosts is None else set(allowed_hosts)
    valid=athlete_index(hs,milb)
    old=cache if isinstance(cache,dict) else {}
    cached=old.get("clips",{}) if old.get("schema")==1 else {}
    if not isinstance(cached,dict):
        cached={}
    manifest_ok=(isinstance(manifest,dict) and manifest.get("schema")==1
                 and isinstance(manifest.get("clips"),list)
                 and len(manifest["clips"])<=100)
    clips=manifest["clips"] if manifest_ok else []
    decisions=[]
    next_cache={}
    processed=0
    cached_count=0
    seen=set()
    for entry in clips:
        cid=entry.get("clip_id") if isinstance(entry,dict) else None
        row={
            "clip_id":cid, "pool":entry.get("pool") if isinstance(entry,dict) else None,
            "player_id":str(entry.get("player_id") or "") if isinstance(entry,dict) else "",
            "player_name":entry.get("player_name") if isinstance(entry,dict) else None,
            "recorded_on":entry.get("recorded_on") if isinstance(entry,dict) else None,
            "source_page_url":entry.get("source_page_url") if isinstance(entry,dict) else None,
            "status":None,
        }
        failure=allowed_clip_metadata(entry,valid,as_of)
        if cid in seen:
            failure="DUPLICATE_CLIP_ID"
        seen.add(cid)
        if not failure and not safe_video_url(entry["video_url"],hosts):
            failure="VIDEO_HOST_NOT_EXPLICITLY_ALLOWED"
        if failure:
            row["status"]=failure
            decisions.append(row)
            continue
        token=clip_fingerprint(entry)
        stored=cached.get(cid)
        if (isinstance(stored,dict) and stored.get("fingerprint")==token
                and stored.get("model_version")==MODEL_VERSION):
            result=stored["result"]
            next_cache[cid]=stored
            cached_count+=1
            row["status"]="ANALYZED_CACHED" if result["quality_pass"] else "LOW_QUALITY_CACHED"
        elif processed>=MAX_NEW_CLIPS_PER_RUN:
            row["status"]="RUN_CLIP_PROCESSING_LIMIT_REACHED"
            decisions.append(row)
            continue
        else:
            processed+=1
            try:
                with tempfile.TemporaryDirectory(prefix="card_bot_film_") as work:
                    path=fetch_video(entry,hosts,work)
                    result=analyze_video(path,entry)
                next_cache[cid]={
                    "fingerprint":token,"model_version":MODEL_VERSION,
                    "result":result,
                }
                row["status"]=("ANALYZED_REVIEW_REQUIRED" if result["quality_pass"]
                               else "INSUFFICIENT_FOOTAGE_QUALITY")
            except Exception as exc:
                # Fail closed on missing model, unavailable clip, invalid
                # checksum, decoder, or source rights; no phantom features.
                row["status"]="VIDEO_ANALYSIS_FAILED"
                row["failure_type"]=type(exc).__name__
                decisions.append(row)
                continue
        row.update({
            "quality_pass":result["quality_pass"],
            "quality_reasons":result["quality_reasons"],
            "repetitions_usable":result["repetitions_usable"],
            "repetitions_annotated":result["repetitions_annotated"],
            "camera_view":entry["camera_view"],
            "camera_id":entry["camera_id"],
            "action":entry["action"],
            "screen_space_angle_features":result["screen_space_angle_features"],
            "model_version":MODEL_VERSION,
            "skill_improvement_verified":False,
            "card_buy_eligible":False,
        })
        decisions.append(row)
    # Rebuild comparisons only from still-manifested, source-verified clips
    # with quality passing; removing a row removes its data from the board.
    groups=defaultdict(list)
    observed={}
    for row in decisions:
        if row["status"] in {"ANALYZED_REVIEW_REQUIRED","ANALYZED_CACHED",
                             "INSUFFICIENT_FOOTAGE_QUALITY","LOW_QUALITY_CACHED"}:
            k=(row["pool"],row["player_id"])
            observed[k]=("VIDEO_2D_POSE_REVIEW_REQUIRED"
                         if row["quality_pass"] else
                         "VIDEO_AVAILABLE_BUT_QUALITY_GATE_FAILED")
            groups[k].append(row)
    comparisons=[]
    for (pool,pid), observations in sorted(groups.items()):
        group_by_camera=defaultdict(list)
        for row in observations:
            group_by_camera[(row["action"],row["camera_id"],
                             row["camera_view"])].append(row)
        for (action,camera_id,camera_view), rows in sorted(group_by_camera.items()):
            comparison=compare_same_camera_observations(rows)
            comparisons.append({
                "pool":pool,"player_id":pid,
                "name":valid.get((pool,pid)),
                "action":action,"camera_id":camera_id,"camera_view":camera_view,
                **comparison,
            })
    queue=athlete_queue(hs,milb,scout,observed)
    clean_cache={"schema":1,"clips":dict(list(sorted(next_cache.items()))[-MAX_CACHE_ENTRIES:])}
    return ({
        "schema":"CARD_BOT_VISUAL_EVIDENCE_V1",
        "model_version":MODEL_VERSION,
        "as_of":as_of.isoformat(),
        "manifest_status":("VALID" if manifest_ok else "MISSING_OR_INVALID"),
        "verified_source_players_in_queue":len(queue),
        "manifest_entries":len(clips),
        "video_clips_newly_processed":processed,
        "video_clips_reused_from_verified_cache":cached_count,
        "quality_passed_clips":sum(bool(x.get("quality_pass")) for x in decisions),
        "confirmed_visual_breakouts":0,
        "actual_card_buy_candidates_from_video":0,
        "approved_host_configuration_present":bool(hosts),
        "clips":decisions,"comparisons":comparisons,"athletes":queue,
        "note":"Actual pose inference ONLY for licensed, SHA-verified, manually "
               "attributed clips. 2D body pose values depend heavily on "
               "camera, crop, event alignment and occlusion. All visual "
               "movement interpretations require trained human scout "
               "review and future validation. No videos, faces or frames "
               "are retained, and visual scores never authorize a card buy.",
    },clean_cache)


def render_markdown(report):
    lines=[
        "# Card Bot — Actual Video Scouting Evidence",
        "",
        f"**Last run:** {report['as_of']} | **Engine:** {report['model_version']}",
        "",
        "## What the system has ACTUALLY seen",
        "",
        f"- Player names queued for filming: **{report['verified_source_players_in_queue']}** (roster or stats records, **not** video).",
        f"- Footage items submitted with human source/identity/licensing records: **{report['manifest_entries']}**.",
        f"- Newly decoded videos: **{report['video_clips_newly_processed']}**; prior valid clip analyses reused: **{report['video_clips_reused_from_verified_cache']}**.",
        f"- Clips meeting image/pose/rep gates: **{report['quality_passed_clips']}**.",
        "- Automatically validated visual skill breakouts: **0**.",
        "- Video-based card-buy authorizations: **0**.",
        "",
        "**IMPORTANT:** If no qualifying video clips are present, Card Bot has "
        "**not watched any players**. A player being on the draft or MiLB "
        "research list does not mean the engine has reviewed film.",
        "",
        "## Individual footage audit",
        "",
        "| Source/player | Recorded | Video source | Frame/pose result | Quality limits |",
        "|---|---|---|---|---|",
    ]
    if not report["clips"]:
        lines.append("| — | — | — | AWAITING LICENSED VIDEO WITH MANUALLY VERIFIED ATHLETE | — |")
    for row in report["clips"]:
        src=row.get("source_page_url") or ""
        source=("[Original source]("+src+")"
                if isinstance(src,str) and src.startswith("https://")
                else "no verified source")
        reasons=", ".join(row.get("quality_reasons") or []) or "—"
        lines.append(
            f"| {row.get('pool')} / {row.get('player_name')} "
            f"({row.get('clip_id')}) | {row.get('recorded_on')} | "
            f"{source} | {row['status']} | {reasons} |"
        )
    lines += ["",
              "## Historical comparisons requiring a human scout",
              "",
              "Comparisons require **two distinct dates, matching camera setup and "
              "view, matching action type, and multiple usable actions per "
              "clip**. Reported angles are *screen-space measurements*, "
              "not performance ratings.",
              ""]
    if not report["comparisons"]:
        lines.append("No usable video comparisons yet.")
    else:
        for row in report["comparisons"]:
            lines.append(
                f"- **{row.get('name')}** ({row['action']}, {row['camera_view']}): "
                f"{row['status']}."
            )
            for name,metrics in (row.get("screen_space_changes") or {}).items():
                lines.append(
                    f"  - {name}: {metrics['earlier_median_screen_deg']}° → "
                    f"{metrics['later_median_screen_deg']}° "
                    f"({metrics['delta_screen_deg']:+.1f}°); "
                    "requires expert review"
                )
    lines += ["",
              "## Full player film-acquisition queue",
              "",
              "**This is a research to-do list, NOT a list of players whose footage "
              "was watched or whose development is confirmed.**",
              "",
              "| Player | Pool | Baseball data status | Footage status | Next task |",
              "|---|---|---|---|---|"]
    for row in report["athletes"]:
        lines.append(
            f"| {row['name']} | {row['pool']} | {row['baseball_evidence']} "
            f"| {row['video_status']} | {row['film_priority']} |"
        )
    lines += [
        "",
        "## Evidence limits and safeguards",
        "",
        "- Video clips must be source-authenticated, legally authorized for analysis, "
        "manually athlete-verified, SHA256-verified and timestamp-annotated.",
        "- The engine decodes frames, uses a pose landmark model to calculate "
        "2D screen angles and between-repetition variation, and rejects low "
        "resolution, poor-sharpness, missing-pose or unmatched-camera studies.",
        "- No face identification, identity matching from images, automatic "
        "pitch classification, release-point inference or injury prediction.",
        "- No pixel/video storage in GitHub outputs. Downloaded clips exist "
        "only in a temporary work directory during processing.",
        "- Baseball value must be validated against future game performance "
        "before visual measurements contribute to probabilities or card-buy decisions.",
        "- The 2027 high-school and 2026 MiLB statistics boards continue "
        "unchanged; the $100 paper ledger remains separate.",
        ""]
    return "\n".join(lines)


def write_report(report,cache,*,json_file=OUTPUT_JSON,md_file=OUTPUT_MD,
                 cache_file=CACHE_PATH):
    for path,data in [
        (json_file,json.dumps(report,sort_keys=True,indent=2)+"\n"),
        (md_file,render_markdown(report)+"\n"),
        (cache_file,json.dumps(cache,sort_keys=True,indent=2)+"\n"),
    ]:
        target=Path(path)
        target.parent.mkdir(parents=True,exist_ok=True)
        fd=None
        # Atomic replacement preserves integrity after GitHub runner errors.
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=target.name+".", delete=False) as handle:
            handle.write(data)
            name=handle.name
        os.replace(name,target)


def main(argv=None):
    parser=argparse.ArgumentParser(description="Evidence-only actual video scan")
    parser.add_argument("--as-of",type=date.fromisoformat,default=date.today())
    parser.add_argument("--needs-runtime",action="store_true")
    parser.add_argument("--manifest",default=MANIFEST_PATH)
    args=parser.parse_args(argv)
    manifest=load_json(args.manifest,{"schema":1,"clips":[]})
    if args.needs_runtime:
        # Avoid costly optional CV installs until at least one valid, allowed
        # video actually exists. Do not treat manifest rows as pose evidence.
        hs=load_json(HS_INDEX_PATH,{})
        mi=load_json(MILB_INDEX_PATH,{})
        valid=athlete_index(hs,mi)
        hosts=trusted_hosts()
        clips=manifest.get("clips",[]) if isinstance(manifest,dict) else []
        eligible=any(
            allowed_clip_metadata(c,valid,args.as_of) is None
            and safe_video_url(c["video_url"],hosts)
            for c in clips if isinstance(c,dict)
        )
        print("1" if eligible else "0")
        return
    hs=load_json(HS_INDEX_PATH,{})
    mi=load_json(MILB_INDEX_PATH,{})
    scout=load_json(SCOUTING_INDEX_PATH,{})
    cache=load_json(CACHE_PATH,{"schema":1,"clips":{}})
    report,new_cache=scan_video_evidence(manifest,hs,mi,scout,
                                         as_of=args.as_of,cache=cache)
    write_report(report,new_cache)
    print(json.dumps({
        "as_of":report["as_of"],
        "player_queue":report["verified_source_players_in_queue"],
        "clips_declared":report["manifest_entries"],
        "clips_processed":report["video_clips_newly_processed"],
        "clips_pose_quality_passed":report["quality_passed_clips"],
        "visual_skill_breakouts_confirmed":report["confirmed_visual_breakouts"],
        "board":OUTPUT_MD,
    },sort_keys=True))


if __name__=="__main__":
    main()
