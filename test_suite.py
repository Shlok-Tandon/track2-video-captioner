"""Diagnostic test harness for the Track 2 captioning pipeline.

Runs the REAL pipeline over every clip in test_input/tasks_full.json and reports,
per clip and in aggregate:
  - the full 4-style captions (so you can eyeball accuracy + tone yourself)
  - silent failures: any caption that is actually a SAFE_FALLBACK string
  - collapsed humour: humorous_tech vs humorous_non_tech too similar
  - missing tech reference in humorous_tech
  - per-clip and total wall-clock time (your 10-minute ceiling check)

Run from the repo root:
    python test_suite.py
(Set your key first: src/embedded_key.py or FIREWORKS_API_KEY env var.)
"""
import json
import sys
import time
from difflib import SequenceMatcher

sys.path.insert(0, ".")
from src.main import process_task          # noqa: E402
from src.pipeline import SAFE_FALLBACK     # noqa: E402

NEED = ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
# Rough lexical hint list; absence isn't proof, but it's a useful flag.
TECH_HINTS = ("code", "server", "bug", "deploy", "api", "algorithm", "cpu",
              "gpu", "cache", "network", "crash", "loop", "database", "cloud",
              "kernel", "compile", "boot", "byte", "pixel", "render", "latency",
              "bandwidth", "runtime", "stack", "commit", "patch", "firmware")


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def check_clip(task_id: str, caps: dict) -> list:
    flags = []
    for style in NEED:
        text = caps.get(style, "")
        if not text:
            flags.append(f"MISSING key: {style}")
            continue
        if text.strip() == SAFE_FALLBACK.get(style, "").strip():
            flags.append(f"FALLBACK (silent failure): {style}")
    th, hn = caps.get("humorous_tech", ""), caps.get("humorous_non_tech", "")
    if th and hn and similar(th, hn) > 0.6:
        flags.append(f"COLLAPSED humour: tech vs non_tech {similar(th, hn):.2f} similar")
    if th and not any(h in th.lower() for h in TECH_HINTS):
        flags.append("humorous_tech has NO obvious tech reference")
    return flags


def main():
    with open("test_input/tasks_full.json") as f:
        tasks = json.load(f)

    print(f"Running pipeline over {len(tasks)} clips...\n" + "=" * 70)
    all_flags, t0 = {}, time.time()

    for task in tasks:
        tid = task.get("task_id", "?")
        cat = task.get("_category", "uncategorised")
        c0 = time.time()
        result = process_task(task)
        dt = time.time() - c0
        caps = result.get("captions", {})

        print(f"\n[{tid}] category: {cat}   ({dt:.1f}s)")
        for style in NEED:
            print(f"  {style:20s}: {caps.get(style, '<<MISSING>>')}")
        flags = check_clip(tid, caps)
        if flags:
            all_flags[tid] = flags
            for fl in flags:
                print(f"  !! {fl}")

    total = time.time() - t0
    print("\n" + "=" * 70)
    print(f"TOTAL: {len(tasks)} clips in {total:.1f}s "
          f"(avg {total/max(len(tasks),1):.1f}s/clip)")
    ceiling = 10 * 60
    print(f"10-min ceiling: {'OK, margin ' + str(int(ceiling-total)) + 's' if total < ceiling else 'OVER BUDGET'}")
    if all_flags:
        print(f"\n{len(all_flags)} clip(s) with flags: {', '.join(all_flags)}")
        print("Investigate these before submitting.")
    else:
        print("\nNo flags. Every clip has 4 real, distinct, non-fallback captions.")


if __name__ == "__main__":
    main()