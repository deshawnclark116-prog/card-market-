"""Bounded, footage-based 2D body-pose observations for Card Bot.

This extracts REAL image-frame landmarks from approved videos using a pinned
MediaPipe pose model, not synthetic scouting narratives. Observations are
research-only; no skill-value conclusions, identity recognition, injury
assessment, bat-speed, pitch-speed, spin, or card purchases.

A human must document the athlete, usage rights, crop, camera viewpoint,
and action timestamps. A single-person pose detector cannot identify which
athlete is on screen or infer which frames contain a hit or pitch.
"""
from __future__ import annotations

import hashlib
import ipaddress
import math
import os
import re
import statistics
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

MODEL_VERSION = "videopose_2d_mediapipe_0_10_21_v1"
MAX_VIDEO_BYTES = 42 * 1024 * 1024
MAX_DURATION_SECONDS = 75
MAX_REPS = 8
FRAMES_PER_REP = 12
MIN_VALID_FRAMES_PER_REP = 7
MIN_VALID_REPS = 3
VISIBILITY_MIN = 0.65
MIN_BLUR_SCORE = 28.0
MIN_WIDTH = 480
MIN_HEIGHT = 320
VIEWS = {"side", "front", "rear", "oblique"}
ACTIONS = {"pitch", "swing", "throw", "field"}
POOLS = {"HS_2027", "MILB_2026"}
SHA_PATTERN = re.compile(r"^[a-f0-9]{64}$")
CLIP_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{2,63}$")

# Exact allowed source hosts are a *repository owner* setting, never supplied
# inside individual untrusted manifest rows. No generic HTTP, no localhost.
def trusted_hosts():
    return {s.strip().lower() for s in
            os.environ.get("CARD_BOT_VIDEO_ALLOWED_HOSTS", "").split(",")
            if s.strip()}


def safe_video_url(url, hosts):
    if not isinstance(url, str) or len(url) > 2048:
        return False
    try:
        parsed = urllib.parse.urlsplit(url)
        hostname = parsed.hostname
        if (parsed.scheme != "https" or not hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443)
                or hostname.lower() not in hosts
                or parsed.fragment):
            return False
        # DNS rebinding is not solved here; allowlist MUST consist of trusted
        # media hosts the repository owner controls or is permitted to use.
        try:
            if not ipaddress.ip_address(hostname).is_global:
                return False
        except ValueError:
            pass
        return True
    except (ValueError, TypeError):
        return False


def allowed_clip_metadata(row, valid_athletes, as_of):
    """Check every field before video access; no best-guess name joins."""
    if not isinstance(row, dict):
        return "INVALID_ROW"
    cid = row.get("clip_id")
    if not isinstance(cid, str) or not CLIP_ID_PATTERN.fullmatch(cid):
        return "INVALID_CLIP_ID"
    pool, pid = row.get("pool"), str(row.get("player_id") or "")
    if pool not in POOLS or (pool, pid) not in valid_athletes:
        return "ATHLETE_ID_NOT_IN_VERIFIED_SCOUTING_POOL"
    if row.get("player_name") != valid_athletes[(pool, pid)]:
        return "PLAYER_NAME_ID_MISMATCH"
    if row.get("athlete_visible_verified_by_reviewer") is not True:
        return "ATHLETE_NOT_MANUALLY_VERIFIED"
    reviewer = row.get("reviewer")
    if not isinstance(reviewer, str) or len(reviewer.strip()) < 3:
        return "MISSING_HUMAN_REVIEWER"
    if row.get("single_player_crop_verified") is not True:
        return "SINGLE_ATHLETE_CROP_NOT_VERIFIED"
    if row.get("usage_rights") not in {"owned", "licensed", "permission"}:
        return "NO_DOCUMENTED_VIDEO_USAGE_RIGHTS"
    rights = row.get("rights_record")
    if not isinstance(rights, str) or not rights.strip() or len(rights) > 500:
        return "MISSING_LICENSE_OR_PERMISSION_RECORD"
    for fld in ("source_page_url", "video_url"):
        if not isinstance(row.get(fld), str) or not row[fld].startswith("https://"):
            return "INVALID_SOURCE_URL"
    if not isinstance(row.get("sha256"), str) or not SHA_PATTERN.fullmatch(row["sha256"]):
        return "MISSING_VIDEO_SHA256"
    try:
        recorded = date.fromisoformat(row["recorded_on"])
    except (KeyError, ValueError, TypeError):
        return "INVALID_RECORDING_DATE"
    if recorded > as_of or recorded < date(2018, 1, 1):
        return "FUTURE_OR_INVALID_RECORDING_DATE"
    if row.get("camera_view") not in VIEWS:
        return "UNKNOWN_CAMERA_VIEW"
    if row.get("action") not in ACTIONS:
        return "UNKNOWN_ACTION"
    if not isinstance(row.get("camera_id"), str) or not row["camera_id"].strip():
        return "MISSING_CAMERA_ID"
    crop = row.get("athlete_crop")
    if (not isinstance(crop, list) or len(crop) != 4 or
            any(isinstance(v, bool) or not isinstance(v, (int, float))
                or not math.isfinite(v) for v in crop)):
        return "INVALID_ATHLETE_CROP"
    x, y, w, h = crop
    if not (0 <= x < 1 and 0 <= y < 1 and .15 <= w <= 1
            and .15 <= h <= 1 and x+w <= 1 and y+h <= 1):
        return "INVALID_ATHLETE_CROP"
    reps = row.get("repetitions")
    if not isinstance(reps, list) or not 1 <= len(reps) <= MAX_REPS:
        return "INVALID_ANNOTATED_ACTIONS"
    last_end = -1.0
    for r in reps:
        if not isinstance(r, dict):
            return "INVALID_ANNOTATED_ACTIONS"
        start, stop = r.get("start_seconds"), r.get("end_seconds")
        if (isinstance(start, bool) or isinstance(stop, bool) or
                not isinstance(start, (int, float)) or
                not isinstance(stop, (int, float)) or
                not math.isfinite(start) or not math.isfinite(stop) or
                not (0 <= start < stop <= MAX_DURATION_SECONDS) or
                stop-start < .35 or start < last_end):
            return "INVALID_ANNOTATED_ACTIONS"
        last_end = stop
    return None


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Video host redirects require explicit source review")


def fetch_verified_video(row, hosts, temp_dir, opener=None):
    """Direct HTTPS only; bounded bytes; sha256 mandatory; no credentials.

    If the server refuses unredirected downloads, the row is marked
    unavailable rather than bypassing URL or copyright restrictions.
    """
    url=row["video_url"]
    if not safe_video_url(url, hosts):
        raise ValueError("VIDEO_HOST_NOT_EXPLICITLY_ALLOWED")
    # Test injection may supply an opener. Production uses redirect-disabled
    # stdlib opener, avoiding unexpected cross-host fetches.
    op = opener or urllib.request.build_opener(_NoRedirects()).open
    req=urllib.request.Request(url, headers={
        "User-Agent":"CardBotVideoAudit/1.0",
        "Accept":"video/mp4,video/quicktime,application/octet-stream",
    })
    out=Path(temp_dir) / (row["clip_id"]+".video")
    digest=hashlib.sha256()
    count=0
    with op(req,timeout=18) as stream, open(out,"wb") as fh:
        while True:
            chunk=stream.read(65536)
            if not chunk:
                break
            count+=len(chunk)
            if count>MAX_VIDEO_BYTES:
                raise ValueError("VIDEO_EXCEEDS_DOWNLOAD_LIMIT")
            digest.update(chunk)
            fh.write(chunk)
    if not count or digest.hexdigest()!=row["sha256"]:
        raise ValueError("VIDEO_SHA256_MISMATCH")
    return out


def angle_degrees(a,b,c):
    """Signed camera-independent? NO: angle is only 2D screen-space."""
    u=(a[0]-b[0],a[1]-b[1])
    v=(c[0]-b[0],c[1]-b[1])
    nu=math.hypot(*u)
    nv=math.hypot(*v)
    if nu < 1e-5 or nv < 1e-5:
        return None
    dot=sum(x*y for x,y in zip(u,v))/(nu*nv)
    return round(math.degrees(math.acos(max(-1.,min(1.,dot)))),3)


# MediaPipe PoseLandmark official 33-landmark indices (NOT face identity).
SHOULDER_LEFT, SHOULDER_RIGHT = 11, 12
ELBOW_LEFT, ELBOW_RIGHT = 13, 14
WRIST_LEFT, WRIST_RIGHT = 15, 16
HIP_LEFT, HIP_RIGHT = 23, 24
KNEE_LEFT, KNEE_RIGHT = 25, 26
ANKLE_LEFT, ANKLE_RIGHT = 27, 28


def frame_pose_features(landmarks):
    """Pure math over normalized pose landmarks; None if quality too poor."""
    if landmarks is None or len(landmarks) < 29:
        return None
    def pt(i):
        p=landmarks[i]
        visibility=float(getattr(p,"visibility",0))
        if visibility < VISIBILITY_MIN:
            return None
        x,y=float(p.x),float(p.y)
        return (x,y) if math.isfinite(x) and math.isfinite(y) else None

    features={}
    def add_angle(name, a,b,c):
        values=[pt(i) for i in (a,b,c)]
        if all(v is not None for v in values):
            v=angle_degrees(*values)
            if v is not None:
                features[name]=v
    add_angle("left_elbow_screen_deg",SHOULDER_LEFT,ELBOW_LEFT,WRIST_LEFT)
    add_angle("right_elbow_screen_deg",SHOULDER_RIGHT,ELBOW_RIGHT,WRIST_RIGHT)
    add_angle("left_knee_screen_deg",HIP_LEFT,KNEE_LEFT,ANKLE_LEFT)
    add_angle("right_knee_screen_deg",HIP_RIGHT,KNEE_RIGHT,ANKLE_RIGHT)
    shoulders=[pt(i) for i in (SHOULDER_LEFT,SHOULDER_RIGHT)]
    hips=[pt(i) for i in (HIP_LEFT,HIP_RIGHT)]
    if all(p is not None for p in shoulders+hips):
        shoulder_mid=tuple((shoulders[0][i]+shoulders[1][i])/2 for i in (0,1))
        hip_mid=tuple((hips[0][i]+hips[1][i])/2 for i in (0,1))
        dx=shoulder_mid[0]-hip_mid[0]
        dy=shoulder_mid[1]-hip_mid[1]
        if math.hypot(dx,dy)>0.03:
            features["trunk_tilt_screen_deg"]=round(
                math.degrees(math.atan2(abs(dx),abs(dy))),3)
    return features if len(features)>=2 else None


def _median(values):
    return round(statistics.median(values),3) if values else None


def summarize_annotated_reps(samples, *, width=640, height=480):
    """samples: per-rep list of (pose_features_or_None, blur_score).

    Trajectory repeatability is measured as between-rep variation in
    angle at equal normalized action phases, not pitching performance.
    """
    reps=[]
    blur_values=[]
    for rep in samples:
        fields={}
        valid=0
        for features,blur in rep:
            if blur is not None and math.isfinite(blur):
                blur_values.append(float(blur))
            if features:
                valid+=1
                for label,v in features.items():
                    fields.setdefault(label,[]).append(float(v))
        if valid >= MIN_VALID_FRAMES_PER_REP:
            rep_metrics={k:_median(v) for k,v in fields.items()
                         if len(v)>=MIN_VALID_FRAMES_PER_REP}
            if len(rep_metrics)>=2:
                reps.append({"metrics":rep_metrics,"valid_frames":valid,
                             "frames_sampled":len(rep)})
    motion={}
    if reps:
        metric_names=set.intersection(*(set(r["metrics"]) for r in reps))
        for name in sorted(metric_names):
            values=[r["metrics"][name] for r in reps]
            motion[name]={"median_screen_deg":_median(values),
                          "between_rep_sd_screen_deg":round(statistics.pstdev(values),3),
                          "reps":len(values)}
    reasons=[]
    if width<MIN_WIDTH or height<MIN_HEIGHT:
        reasons.append("LOW_VIDEO_RESOLUTION")
    if len(reps)<MIN_VALID_REPS:
        reasons.append("INSUFFICIENT_VALID_POSE_REPETITIONS")
    blur=_median(blur_values)
    if blur is None or blur<MIN_BLUR_SCORE:
        reasons.append("LOW_OR_UNKNOWN_FRAME_SHARPNESS")
    if len(motion)<2:
        reasons.append("INSUFFICIENT_SHARED_BODY_ANGLES")
    return {
        "quality_pass":not reasons,
        "quality_reasons":reasons,
        "repetitions_usable":len(reps),
        "repetitions_annotated":len(samples),
        "resolution":f"{width}x{height}",
        "blur_laplacian_variance_median":blur,
        "screen_space_angle_features":motion,
        "interpretation":"2D pose observations only; no biomechanical skill grading",
    }


def analyze_local_video(video_file, row, *, cv2_module=None, pose_factory=None):
    """Actually decode frames and run body-pose inference; no internet.

    MediaPipe 0.10.21 legacy Pose is pinned in requirements-video.txt.
    Python-only fixture injection makes entire decoding and feature pipeline
    testable without downloading any private or copyrighted footage.
    """
    if cv2_module is None:
        import cv2 as cv2_module
    cv2=cv2_module
    if pose_factory is None:
        import mediapipe as mp
        if not hasattr(mp, "solutions"):
            raise RuntimeError("MEDIAPIPE_LEGACY_POSE_NOT_AVAILABLE")
        pose_factory=lambda:mp.solutions.pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.6,
        )
    cap=cv2.VideoCapture(str(video_file))
    if not cap.isOpened():
        cap.release()
        raise ValueError("VIDEO_DECODER_CANNOT_OPEN_FILE")
    try:
        width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps=float(cap.get(cv2.CAP_PROP_FPS))
        frame_count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if (width<=0 or height<=0 or not math.isfinite(fps)
                or fps<5 or fps>240 or frame_count<=0):
            raise ValueError("INVALID_VIDEO_FRAME_METADATA")
        duration=frame_count/fps
        if duration>MAX_DURATION_SECONDS+2:
            raise ValueError("VIDEO_LONGER_THAN_APPROVED_LIMIT")
        reps=[]
        with pose_factory() as pose:
            for rep in row["repetitions"]:
                start,stop=rep["start_seconds"],rep["end_seconds"]
                if stop>duration+.15:
                    raise ValueError("ANNOTATED_REP_OUTSIDE_VIDEO_DURATION")
                observed=[]
                for j in range(FRAMES_PER_REP):
                    t=start+(stop-start)*(j+.5)/FRAMES_PER_REP
                    # Seeking is deliberate; static-image pose model independently
                    # detects each frame, avoiding tracker state assumptions.
                    cap.set(cv2.CAP_PROP_POS_MSEC,t*1000)
                    ok,frame=cap.read()
                    if not ok or frame is None:
                        observed.append((None,None))
                        continue
                    x,y,w,h=row["athlete_crop"]
                    h_px,w_px=frame.shape[:2]
                    frame=frame[int(y*h_px):int((y+h)*h_px),
                                int(x*w_px):int((x+w)*w_px)]
                    if not frame.size:
                        observed.append((None,None))
                        continue
                    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
                    sharp=float(cv2.Laplacian(gray,cv2.CV_64F).var())
                    rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                    inference=pose.process(rgb)
                    lm=getattr(getattr(inference,"pose_landmarks",None),
                               "landmark",None)
                    observed.append((frame_pose_features(lm),sharp))
                reps.append(observed)
        crop=row["athlete_crop"]
        result=summarize_annotated_reps(
            reps,width=int(width*crop[2]),height=int(height*crop[3]))
        result.update({
            "model_version":MODEL_VERSION,
            "sampled_frames":len(reps)*FRAMES_PER_REP,
            "video_duration_seconds":round(duration,2),
            "fps_source":round(fps,2),
            "camera_view":row["camera_view"],
            "action":row["action"],
            "frame_or_face_data_persisted":False,
        })
        return result
    finally:
        cap.release()


def compare_same_camera_observations(observations):
    """Compare two clips from different dates WITHOUT judging improvement."""
    valid=[x for x in observations if x.get("quality_pass")]
    valid.sort(key=lambda x:(x["recorded_on"],x["clip_id"]))
    if len(valid)<2:
        return {"status":"INSUFFICIENT_VALID_MULTI_DATE_VIDEO"}
    older,later=valid[-2:]
    if older["recorded_on"]==later["recorded_on"]:
        return {"status":"NO_INDEPENDENT_SECOND_DATE"}
    if (older["camera_view"]!=later["camera_view"] or
            older["camera_id"]!=later["camera_id"] or
            older["action"]!=later["action"]):
        return {"status":"CAMERAS_OR_ACTIONS_NOT_COMPARABLE"}
    left=older.get("screen_space_angle_features") or {}
    right=later.get("screen_space_angle_features") or {}
    change={}
    for k in sorted(left.keys() & right.keys()):
        a,b=left[k],right[k]
        change[k]={
            "earlier_median_screen_deg":a["median_screen_deg"],
            "later_median_screen_deg":b["median_screen_deg"],
            "delta_screen_deg":round(b["median_screen_deg"]-a["median_screen_deg"],3),
            "earlier_between_rep_sd_screen_deg":a["between_rep_sd_screen_deg"],
            "later_between_rep_sd_screen_deg":b["between_rep_sd_screen_deg"],
        }
    if len(change)<2:
        return {"status":"INSUFFICIENT_MATCHED_POSE_FEATURES"}
    return {
        "status":"OBSERVED_2D_POSE_CHANGE_HUMAN_SCOUT_REVIEW_REQUIRED",
        "earlier_date":older["recorded_on"],
        "later_date":later["recorded_on"],
        "earlier_clip":older["clip_id"],
        "later_clip":later["clip_id"],
        "screen_space_changes":change,
        "skill_improvement_verified":False,
        "performance_projection_changed":False,
        "card_buy_eligible":False,
        "note":"Camera and clip-window geometry affect 2D angles. "
               "Do NOT interpret angle/variability changes as better "
               "mechanics, pitch command, hitting quality, or injury risk.",
    }
