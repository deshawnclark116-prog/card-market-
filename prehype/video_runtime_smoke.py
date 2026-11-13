"""Original synthetic clip runtime smoke: proves real CV + MediaPipe can execute.

Synthetic shape frames are generated in memory and never falsely assigned
to a minor/prospect. They are NOT a benchmark of athletic pose accuracy.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from prehype.video_evidence import MODEL_VERSION, analyze_local_video


def smoke():
    import cv2
    import mediapipe as mp
    import numpy as np

    if not hasattr(mp, "solutions") or not hasattr(mp.solutions, "pose"):
        raise RuntimeError("PINNED_MEDIAPIPE_POSE_MODEL_MISSING")
    with tempfile.TemporaryDirectory(prefix="card_bot_original_synthetic_") as temp:
        movie=Path(temp)/"synthetic_moving_shapes.avi"
        writer=cv2.VideoWriter(str(movie),cv2.VideoWriter_fourcc(*"MJPG"),15,(640,480))
        if not writer.isOpened():
            raise RuntimeError("OPENCV_SYNTHETIC_VIDEO_ENCODER_UNAVAILABLE")
        try:
            for frame_i in range(105):  # 7 seconds; multiple action windows
                frame=np.zeros((480,640,3),dtype=np.uint8)
                x=60+(frame_i*3)%430
                # Rectangles, NOT a generated athlete or actual minor face.
                cv2.rectangle(frame,(x,170),(x+48,315),(150,150,150),-1)
                cv2.line(frame,(x+23,200),(x+72,140),(240,240,240),7)
                writer.write(frame)
        finally:
            writer.release()
        row={
            "camera_view":"side","camera_id":"original_shapes_cam",
            "action":"pitch","athlete_crop":[0,0,1,1],
            "repetitions":[
                {"start_seconds":.25,"end_seconds":1.55},
                {"start_seconds":2.15,"end_seconds":3.5},
                {"start_seconds":4.15,"end_seconds":5.55},
            ],
        }
        observed=analyze_local_video(movie,row)
        if observed["sampled_frames"]!=36 or not observed["model_version"]==MODEL_VERSION:
            raise RuntimeError("POSE_DECODER_SMOKE_INCOMPLETE")
        if observed["fps_source"]<=0 or observed["video_duration_seconds"]<6.5:
            raise RuntimeError("POSE_DECODER_SMOKE_BAD_METADATA")
        # A self-test is never a historical video of a specific athlete.
        return {
            "result":"OK_REAL_OPENCV_AND_MEDIAPIPE_EXECUTION",
            "model_version":MODEL_VERSION,
            "sampled_frames":observed["sampled_frames"],
            "fps":observed["fps_source"],
            "pose_reps_detected_on_original_shapes":observed["repetitions_usable"],
            "synthetic_artwork_is_not_a_scouted_player":True,
        }


if __name__=="__main__":
    print(json.dumps(smoke(),sort_keys=True))
