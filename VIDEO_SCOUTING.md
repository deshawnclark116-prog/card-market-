# Card Bot — Actual Video Scouting, v1

## What is implemented

**A video inference pipeline, not an automated scout's opinion generator.**

- **OpenCV** decodes actual MP4/MOV frames and checks resolution, frame rate and sharpness.
- **MediaPipe Pose** (version 0.10.21) detects 33 body landmarks on athlete-cropped frames.
- Numeric research outputs: observed two-dimensional **elbow and knee angles, trunk tilt**, and variation across action repetitions. These are NOT bat speed, pitch velocity, true 3D biomechanics, pitch movement, injury risk or projected MLB ability.
- Requires documented video rights, original source, exact manually verified athlete identity, SHA256 checksum, clip date, fixed single-athlete crop, camera setup and annotated pitch/swing repetitions.
- Quality gating: minimum three observable actions, 12 sampled frames each, at least seven usable pose frames per action, usable sharpness/resolution and common body angles. Insufficient evidence is explicitly rejected.
- Cross-date comparisons require matching camera ID, angle and activity. Every detected change is **HUMAN SCOUT REVIEW REQUIRED**, never a skill improvement or purchase signal.
- Clip analyses are cached against content SHA, annotations, player, model version, and source rights. Each new video is limited to 42 MiB, 75 seconds, eight action repetitions; up to six new clips per run. Temporary downloads are deleted and no video/face/frame data appears in the research output.
- Uses both the 2027 high-school and 2026 MiLB player IDs. Every queue member is visible whether or not footage exists, with an accurate **NO_APPROVED_FOOTAGE_ANALYZED** status.
- The daily GitHub workflow publishes [VIDEO_SCOUTING_BOARD.md](VIDEO_SCOUTING_BOARD.md) and [source audit JSON](data/card_bot_video_scouting_latest.json), without affecting the $100 card ledger.

## No footage means the bot has not watched anyone

A public roster, a reported fastball peak or a video search link is not a video. Current card research does not supply automatically licensed player film.

The system does **not** scrape YouTube, Perfect Game, ESPN, broadcasts or subscriber videos, bypass copyright, pretend source video is available, identify faces, or assume that being able to watch online confers permission to download/analyze.

**Until a verified clip is actually analyzed, the visual scouting count is zero.** The pipeline is installed to handle video; it does not claim it has already reviewed footage.

## Adding a real clip

1. Obtain the clip and written permission/rights for analysis. Verify the visible player manually and match the exact ID in the class-2027 or MiLB research JSON. Do not publish identifying personal details beyond the public sporting name.
2. Create a short, direct HTTPS video URL on a host you are authorized to use. Configure its exact hostname as GitHub repository variable **CARD_BOT_VIDEO_ALLOWED_HOSTS**. There is no unrestricted video downloader; redirects are blocked.
3. Calculate the video's SHA256 checksum locally (for example, use the sha256sum command). Keep the right-holder/permission record separately; reference it without putting private contact details in GitHub.
4. Edit [data/card_bot_video_manifest.json](data/card_bot_video_manifest.json). The following placeholders describe the format only:

~~~json
{
  "schema": 1,
  "clips": [
    {
      "clip_id": "prep_pitch_2026_jun_a",
      "pool": "HS_2027",
      "player_id": "REPLACE_WITH_VERIFIED_PLAYER_ID",
      "player_name": "REPLACE_WITH_EXACT_ROSTER_NAME",
      "athlete_visible_verified_by_reviewer": true,
      "reviewer": "Person who checked athlete and crop",
      "single_player_crop_verified": true,
      "usage_rights": "permission",
      "rights_record": "External written analysis permission reference",
      "source_page_url": "https://authorized-source.example/event",
      "video_url": "https://your-owned-media.example/clip.mp4",
      "sha256": "REPLACE_WITH_64_LOWERCASE_SHA256_DIGITS",
      "recorded_on": "2026-06-15",
      "camera_view": "side",
      "camera_id": "fixed_cam1_same_view_distance",
      "action": "pitch",
      "athlete_crop": [0.2, 0.1, 0.6, 0.85],
      "repetitions": [
        {"start_seconds": 0.5, "end_seconds": 2.0},
        {"start_seconds": 3.0, "end_seconds": 4.5},
        {"start_seconds": 6.0, "end_seconds": 7.5}
      ]
    }
  ]
}
~~~

Crop is [x, y, width, height] from 0 to 1 of the original frame.
Action timestamps belong to the **short clip**, not full-game timeline.

5. Use [Run workflow](https://github.com/deshawnclark116-prog/card-market-/actions/workflows/card-bot-paper.yml) or let the scheduled GitHub Action run. Computer-vision packages install only for a valid, authorized clip from a trusted host. The comparison board will accumulate dated observations without posting footage or pretending to know unobservable details.

## Scientific and privacy limitations

**2D video is not 3D motion capture.** Changing camera viewpoint, lens or focal length, optical distortion, different lighting, panning, speed changes, changing crop, occlusion or annotation error can produce a false change in visible angles.

Before any footage feature can influence breakout probabilities, obtain repeated observations across dates, properly matched camera setups, blind expert scouting ratings, inter-reviewer agreement, and forward-only holdout tests against actual player performance. A lower between-action variance does not automatically mean better mechanics.

**High-school athletes require particular care.** No private footage access, face recognition, biometric identity fingerprints, hidden tracking, health/injury profiling, or unlicensed redistribution. A reviewer verifies source/identity, and only aggregate numerical pose evidence is kept in GitHub. Visual data NEVER authorizes a card purchase or modifies the $100 paper bankroll.
