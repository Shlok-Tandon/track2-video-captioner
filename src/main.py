"""Entry point: read /input/tasks.json, write /output/results.json.

Always writes a valid results.json and exits 0, even if individual clips
failed - a crash or a dropped style key would zero the score.
"""
import json
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()  # local convenience; absent inside the image
except ImportError:
    pass

from .frame_extractor import extract_frames
from .pipeline import caption_clip, SAFE_FALLBACK

STYLES = ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
INPUT_PATH = os.environ.get("TASKS_INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("RESULTS_OUTPUT_PATH", "/output/results.json")
DEADLINE = time.time() + 9 * 60  # keep 60s of the 10-min ceiling in reserve


def download(url: str, dest: str):
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)


def process_task(task: dict) -> dict:
    task_id = task.get("task_id", "unknown")
    styles = task.get("styles", STYLES)
    fallback = {"task_id": task_id,
                "captions": {s: SAFE_FALLBACK.get(s, "A short video clip.")
                             for s in styles}}
    if time.time() > DEADLINE:            # out of budget -> fallback, not crash
        return fallback
    try:
        with tempfile.TemporaryDirectory() as td:
            video_path = os.path.join(td, "clip.mp4")
            download(task["video_url"], video_path)
            frames = extract_frames(video_path, td)
            if not frames:
                return fallback
            return {"task_id": task_id,
                    "captions": caption_clip(frames, styles)}
    except Exception as e:
        print(f"[warn] task {task_id} fell back: {e}", file=sys.stderr)
        return fallback


def main():
    with open(INPUT_PATH) as f:
        tasks = json.load(f)

    results = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(process_task, t): t for t in tasks}
        for fut in as_completed(futures):
            results.append(fut.result())

    order = {t.get("task_id"): i for i, t in enumerate(tasks)}
    results.sort(key=lambda r: order.get(r["task_id"], 999))

    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {len(results)} results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
