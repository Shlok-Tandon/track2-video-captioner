"""Fast sanity check across a batch of test tasks (no Docker needed).

Run:  python test_local.py
Reads test_input/tasks.json, runs the full pipeline, and asserts every
requested style produced a non-empty caption.
"""
import json
import sys

sys.path.insert(0, ".")
from src.main import process_task

with open("test_input/tasks.json") as f:
    tasks = json.load(f)

for t in tasks:
    result = process_task(t)
    print(json.dumps(result, indent=2))
    for style, caption in result["captions"].items():
        assert caption, f"EMPTY CAPTION for {style} on {t['task_id']}"

print("OK: all tasks produced a non-empty caption for every requested style.")
