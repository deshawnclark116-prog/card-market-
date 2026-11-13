"""Offline regression tests: real-video plumbing must fail closed, never hallucinate."""
import hashlib
from datetime import date
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from prehype.video_evidence import (
    MODEL_VERSION, allowed_clip_metadata, angle_degrees, analyze_local_video,
    compare_same_camera_observations, fetch_verified_video, frame_pose_features,
    safe_video_url, summarize_annotated_reps,
)
from prehype.video_scout import (
    athlete_index, clip_fingerprint, render_markdown, scan_video_evidence,
    write_report,
)

TODAY=date(2026,11,13)
HS={"players":[{"name":"Test Prep Pitcher","player_id":"1701",
                "market_exposure":"COLLECTOR_HYPE_UNKNOWN"}]}
MILB={"players":[{"name":"Test Pro Hitter","player_id":"2701",
                  "development_phase":"CURRENT_UPTREND"}]}
SCOUT={"discovery":{"all_skill_improvement_candidates":[
    {"name":"Test Pro Hitter","player_id":"2701",
     "evidence_tier":"EARLY_14_ONLY"}]}}
ATHLETES=athlete_index(HS,MILB)


def clip(cid="clip_2026_001",date_value="2026-08-01",**overrides):
    values={
        "clip_id":cid, "pool":"HS_2027","player_id":"1701",
        "player_name":"Test Prep Pitcher",
        "athlete_visible_verified_by_reviewer":True,
        "reviewer":"Human source checker",
        "single_player_crop_verified":True,
        "usage_rights":"permission",
        "rights_record":"Written analysis permission is on file; source #123",
        "source_page_url":"https://rights.example/video/provenance",
        "video_url":"https://video.example/approved-player-footage.mp4",
        "sha256":"a"*64,
        "recorded_on":date_value,
        "camera_view":"side","camera_id":"same-fixed-tripod",
        "action":"pitch","athlete_crop":[0.,0.,1.,1.],
        "repetitions":[
            {"start_seconds":0,"end_seconds":1},
            {"start_seconds":2,"end_seconds":3},
            {"start_seconds":4,"end_seconds":5},
        ],
    }
    values.update(overrides)
    return values


def pose():
    p=[NS(x=.4,y=.35,visibility=.94) for _ in range(33)]
    coords={
        11:(.4,.3),12:(.6,.3),13:(.35,.4),14:(.65,.4),
        15:(.40,.55),16:(.60,.55),
        23:(.42,.55),24:(.58,.55),
        25:(.42,.75),26:(.58,.75),27:(.40,.95),28:(.60,.95),
    }
    for i,(x,y) in coords.items():
        p[i].x=x;p[i].y=y
    return p


def valid_pose_result():
    features=frame_pose_features(pose())
    assert len(features)>=2
    return summarize_annotated_reps(
        [[(features,80.) for _ in range(12)] for _ in range(3)],
        width=640,height=480,
    )


def test_pose_math_and_quality_gate_are_real_numbers_not_scout_ratings():
    assert angle_degrees((1,0),(0,0),(0,1))==90
    assert angle_degrees((0,0),(0,0),(0,1)) is None
    features=frame_pose_features(pose())
    assert all(k.endswith("_deg") for k in features)
    assert 0<=features["left_elbow_screen_deg"]<=180
    assert 0<=features["trunk_tilt_screen_deg"]<=90
    out=valid_pose_result()
    assert out["quality_pass"]
    assert out["repetitions_usable"]==3
    assert out["screen_space_angle_features"]
    assert "skill grading" in out["interpretation"]


def test_occluded_pose_and_blurry_single_rep_fail_not_fake_a_rating():
    points=pose()
    points[13].visibility=0
    points[14].visibility=0
    points[25].visibility=0
    points[26].visibility=0
    assert frame_pose_features(points) is None
    out=summarize_annotated_reps(
        [[(None,1.0)]*12 for _ in range(2)],width=220,height=160)
    assert not out["quality_pass"]
    assert "LOW_VIDEO_RESOLUTION" in out["quality_reasons"]
    assert "INSUFFICIENT_VALID_POSE_REPETITIONS" in out["quality_reasons"]


def test_approved_video_hosts_explicit_and_no_private_network_or_http():
    assert safe_video_url("https://video.example/film.mp4",{"video.example"})
    for url in (
        "http://video.example/film.mp4",
        "https://localhost/film.mp4",
        "https://127.0.0.1/film.mp4",
        "https://10.1.2.3/film.mp4",
        "https://user:pass@video.example/film.mp4",
        "https://other.example/film.mp4",
        "https://video.example:8888/film.mp4",
        "https://video.example/film.mp4#token",
    ):
        assert not safe_video_url(url,{"video.example"})


def test_video_permissions_and_manual_player_name_are_hard_gates():
    c=clip()
    assert allowed_clip_metadata(c,ATHLETES,TODAY) is None
    assert allowed_clip_metadata(clip(player_name="Different Athlete"),ATHLETES,TODAY)=="PLAYER_NAME_ID_MISMATCH"
    assert allowed_clip_metadata(clip(athlete_visible_verified_by_reviewer=False),ATHLETES,TODAY)=="ATHLETE_NOT_MANUALLY_VERIFIED"
    assert allowed_clip_metadata(clip(single_player_crop_verified=False),ATHLETES,TODAY)=="SINGLE_ATHLETE_CROP_NOT_VERIFIED"
    assert allowed_clip_metadata(clip(usage_rights="public_web_video"),ATHLETES,TODAY)=="NO_DOCUMENTED_VIDEO_USAGE_RIGHTS"
    assert allowed_clip_metadata(clip(sha256="not_a_sha"),ATHLETES,TODAY)=="MISSING_VIDEO_SHA256"
    assert allowed_clip_metadata(clip(recorded_on="2027-04-14"),ATHLETES,TODAY)=="FUTURE_OR_INVALID_RECORDING_DATE"
    assert allowed_clip_metadata(clip(athlete_crop=[0,.7,.7,.7]),ATHLETES,TODAY)=="INVALID_ATHLETE_CROP"
    assert allowed_clip_metadata(clip(camera_view="unknown"),ATHLETES,TODAY)=="UNKNOWN_CAMERA_VIEW"
    assert allowed_clip_metadata(clip(repetitions=[
        {"start_seconds":2,"end_seconds":3},
        {"start_seconds":1,"end_seconds":4},
    ]),ATHLETES,TODAY)=="INVALID_ANNOTATED_ACTIONS"


def test_real_fetch_bytes_are_bounded_and_checksum_verification(tmp_path):
    raw=b"not a real movie but download checksum is real"
    digest=hashlib.sha256(raw).hexdigest()
    class Response:
        def __init__(self): self._pos=0
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def read(self,n):
            out=raw[self._pos:self._pos+n];self._pos+=len(out);return out
    def opener(req,timeout): return Response()
    path=fetch_verified_video(clip(sha256=digest),{"video.example"},tmp_path,opener=opener)
    assert path.read_bytes()==raw
    with pytest.raises(ValueError,match="VIDEO_SHA256_MISMATCH"):
        fetch_verified_video(clip(),{"video.example"},tmp_path,opener=opener)


def test_no_film_is_zero_footage_even_if_players_are_on_watchlist(tmp_path):
    report,cache=scan_video_evidence({"schema":1,"clips":[]},HS,MILB,SCOUT,
                                    as_of=TODAY,allowed_hosts=set())
    assert report["verified_source_players_in_queue"]==2
    assert report["manifest_entries"]==0
    assert report["video_clips_newly_processed"]==0
    assert report["quality_passed_clips"]==0
    assert report["confirmed_visual_breakouts"]==0
    assert report["actual_card_buy_candidates_from_video"]==0
    md=render_markdown(report)
    assert "has **not watched any players**" in md
    assert "Test Prep Pitcher" in md and "Test Pro Hitter" in md
    assert "NO_APPROVED_FOOTAGE_ANALYZED" in md
    assert not cache["clips"]
    write_report(report,cache,
                 json_file=tmp_path/"evidence.json",
                 md_file=tmp_path/"evidence.md",
                 cache_file=tmp_path/"cache.json")
    assert (tmp_path/"evidence.md").exists()


def test_invalid_or_unlicensed_clip_wont_even_download():
    calls=[]
    def forbidden(*args,**kwargs):
        calls.append(args)
        raise AssertionError("Should NOT fetch")
    report,_=scan_video_evidence({"schema":1,"clips":[clip(usage_rights="unknown")]},
                                 HS,MILB,SCOUT,as_of=TODAY,
                                 allowed_hosts={"video.example"},
                                 fetch_video=forbidden)
    assert report["clips"][0]["status"]=="NO_DOCUMENTED_VIDEO_USAGE_RIGHTS"
    assert not calls


def test_unapproved_host_blocks_even_valid_licensed_manifest():
    report,_=scan_video_evidence({"schema":1,"clips":[clip()]},HS,MILB,SCOUT,
                                 as_of=TODAY,allowed_hosts=set())
    assert report["clips"][0]["status"]=="VIDEO_HOST_NOT_EXPLICITLY_ALLOWED"
    assert report["quality_passed_clips"]==0


def test_empty_or_broken_manifest_doesnt_generate_fake_results():
    report,_=scan_video_evidence({"schema":5,"clips":[clip()]},HS,MILB,SCOUT,
                                 as_of=TODAY,allowed_hosts={"video.example"})
    assert report["manifest_status"]=="MISSING_OR_INVALID"
    assert report["clips"]==[]


def test_real_processing_boundary_uses_analyzer_and_immutable_clip_cache():
    calls=[]
    def fetch(row,hosts,folder):
        calls.append("fetch")
        return Path(folder)/"clip.mp4"
    def analyze(path,row):
        calls.append("analyze")
        return valid_pose_result()
    manifest={"schema":1,"clips":[clip()]}
    result,cache=scan_video_evidence(manifest,HS,MILB,SCOUT,as_of=TODAY,
                                    allowed_hosts={"video.example"},
                                    fetch_video=fetch,analyze_video=analyze)
    assert calls==["fetch","analyze"]
    assert result["quality_passed_clips"]==1
    assert result["video_clips_newly_processed"]==1
    assert result["confirmed_visual_breakouts"]==0
    assert result["clips"][0]["status"]=="ANALYZED_REVIEW_REQUIRED"
    hs_row=next(a for a in result["athletes"] if a["pool"]=="HS_2027")
    assert hs_row["video_status"]=="VIDEO_2D_POSE_REVIEW_REQUIRED"
    result2,cache2=scan_video_evidence(manifest,HS,MILB,SCOUT,as_of=TODAY,
                                      allowed_hosts={"video.example"},
                                      cache=cache,
                                      fetch_video=fetch,analyze_video=analyze)
    assert calls==["fetch","analyze"]
    assert result2["clips"][0]["status"]=="ANALYZED_CACHED"
    assert result2["video_clips_newly_processed"]==0
    assert result2["video_clips_reused_from_verified_cache"]==1
    assert cache==cache2


def test_two_dates_compare_camera_matched_angles_but_never_claim_skill():
    old=valid_pose_result()
    updated=valid_pose_result()
    updated["screen_space_angle_features"]["left_elbow_screen_deg"]["median_screen_deg"]+=7
    def fetch(row,hosts,folder):
        return Path(folder)/"dummy.mp4"
    def analyze(path,row):
        return old if row["clip_id"]=="clip_first" else updated
    manifest={"schema":1,"clips":[clip("clip_first","2026-05-01"),
                                  clip("clip_second","2026-10-10")]}
    result,_=scan_video_evidence(manifest,HS,MILB,SCOUT,as_of=TODAY,
                                 allowed_hosts={"video.example"},fetch_video=fetch,
                                 analyze_video=analyze)
    assert len(result["comparisons"])==1
    c=result["comparisons"][0]
    assert c["status"]=="OBSERVED_2D_POSE_CHANGE_HUMAN_SCOUT_REVIEW_REQUIRED"
    assert c["screen_space_changes"]["left_elbow_screen_deg"]["delta_screen_deg"]==7
    assert c["skill_improvement_verified"] is False
    assert c["card_buy_eligible"] is False
    assert result["confirmed_visual_breakouts"]==0
    assert "7.0°" in render_markdown(result)


def test_unmatched_view_refuses_temporal_comparison():
    features=valid_pose_result()
    older={**features,"camera_view":"front","camera_id":"a","action":"pitch",
           "recorded_on":"2026-02-03","clip_id":"old"}
    later={**features,"camera_view":"side","camera_id":"a","action":"pitch",
           "recorded_on":"2026-10-03","clip_id":"new"}
    assert compare_same_camera_observations([older,later])["status"]=="CAMERAS_OR_ACTIONS_NOT_COMPARABLE"


def test_actual_video_decode_pipeline_runs_with_fake_video_backend():
    class Frame:
        shape=(480,640,3)
        size=640*480*3
        def __getitem__(self,idx): return self
    class Number:
        def var(self): return 55.
    class Capture:
        def isOpened(self): return True
        def get(self,index):
            return {1:640,2:480,3:24,4:240}[index]
        def set(self,index,value): pass
        def read(self): return True,Frame()
        def release(self): pass
    class CV:
        CAP_PROP_FRAME_WIDTH=1
        CAP_PROP_FRAME_HEIGHT=2
        CAP_PROP_FPS=3
        CAP_PROP_FRAME_COUNT=4
        CAP_PROP_POS_MSEC=5
        COLOR_BGR2GRAY=6
        COLOR_BGR2RGB=7
        CV_64F=8
        def VideoCapture(self,path): return Capture()
        def cvtColor(self,frame,code): return frame
        def Laplacian(self,frame,code): return Number()
    class Pose:
        def __enter__(self): return self
        def __exit__(self,*args): return None
        def process(self,frame): return NS(pose_landmarks=NS(landmark=pose()))
    result=analyze_local_video("synthetic.mp4",clip(),
                               cv2_module=CV(),pose_factory=Pose)
    assert result["quality_pass"]
    assert result["sampled_frames"]==36
    assert result["video_duration_seconds"]==10
    assert result["model_version"]==MODEL_VERSION
    assert result["frame_or_face_data_persisted"] is False


def test_validated_clip_metadata_fingerprint_changes_if_camera_or_license_changes():
    assert clip_fingerprint(clip())!=clip_fingerprint(clip(camera_view="front"))
    assert clip_fingerprint(clip())!=clip_fingerprint(clip(rights_record="new written license"))



def test_failed_fetch_never_counts_as_video_watched():
    def fail(row,hosts,temp):
        raise ValueError("VIDEO_SHA256_MISMATCH")
    report,_=scan_video_evidence({"schema":1,"clips":[clip()]},
                                 HS,MILB,SCOUT,as_of=TODAY,
                                 allowed_hosts={"video.example"},
                                 fetch_video=fail)
    assert report["new_video_analysis_attempts"]==1
    assert report["video_clips_newly_processed"]==0
    assert report["quality_passed_clips"]==0
    assert report["clips"][0]["status"]=="VIDEO_ANALYSIS_FAILED"
    assert report["clips"][0]["failure_code"]=="VIDEO_SHA256_MISMATCH"
    assert "Newly decoded and analyzed videos: **0**" in render_markdown(report)


def test_cache_does_not_reuse_with_changed_crop_or_rights():
    calls=[]
    def get(row,hosts,folder):
        calls.append("fetch")
        return Path(folder)/"video.mp4"
    def analyze(path,row):
        calls.append("analyze")
        return valid_pose_result()
    first={"schema":1,"clips":[clip()]}
    _,cache=scan_video_evidence(first,HS,MILB,SCOUT,as_of=TODAY,
                               allowed_hosts={"video.example"},
                               fetch_video=get,analyze_video=analyze)
    revised={"schema":1,"clips":[clip(athlete_crop=[.1,.1,.8,.8])]}
    report,_=scan_video_evidence(revised,HS,MILB,SCOUT,as_of=TODAY,
                                 allowed_hosts={"video.example"},cache=cache,
                                 fetch_video=get,analyze_video=analyze)
    assert calls==["fetch","analyze","fetch","analyze"]
    assert report["video_clips_newly_processed"]==1
    assert report["video_clips_reused_from_verified_cache"]==0
