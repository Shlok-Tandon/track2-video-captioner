"""Extract representative, downscaled frames from a video via ffmpeg."""
import os
import subprocess


def extract_frames(video_path: str, out_dir: str,
                   every_n_seconds: float = 2.5,
                   max_frames: int = 8, width: int = 512) -> list:
    """Sample frames at a fixed interval, downscaled to `width` px wide.

    Downscaling matters: the example clips are UHD, and eight full-res frames
    base64-encoded is a 10-20 MB request that risks the 30s/request limit.
    At 512px each frame is ~40-80 KB with negligible loss for captioning.
    """
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,          # -y BEFORE the output path
            "-vf", f"fps=1/{every_n_seconds},scale={width}:-2",
            "-frames:v", str(max_frames),
            "-q:v", "4",
            os.path.join(out_dir, "frame_%02d.jpg"),
        ],
        check=True, capture_output=True, timeout=60,
    )
    return sorted(
        os.path.join(out_dir, f)
        for f in os.listdir(out_dir) if f.endswith(".jpg")
    )
