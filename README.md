<<<<<<< HEAD
# Track 2 Video Captioning Agent — [Team Name]

An AI agent that watches a short video clip and writes a caption in four styles
(`formal`, `sarcastic`, `humorous_tech`, `humorous_non_tech`). Built for the
AMD Developer Hackathon: ACT II, Track 2.

## How it works
Two stages, so accuracy and tone are tuned independently (matching the judge's
two scoring axes):

```
tasks.json
  -> download clip
  -> ffmpeg sample 8 frames, downscaled to 512px
  -> STAGE A  describe (Gemma vision model)   -> neutral factual description
  -> STAGE B  restyle  (Gemma text model)     -> ONE JSON object, all 4 styles
  -> validate: every style key present + non-empty? else safe fallback
  -> results.json
```

Gemma model used: **`<fill in the exact Fireworks Gemma model ID here>`** — it
powers the core captioning, not a side call.

## Run it (the way the judge does)
```bash
docker pull ghcr.io/<YOU>/track2-captioner:latest
docker run --rm \
  -v "$(pwd)/test_input:/input" \
  -v "$(pwd)/test_output:/output" \
  ghcr.io/<YOU>/track2-captioner:latest
cat test_output/results.json
```

## Build from source
```bash
docker buildx build --platform linux/amd64 -t track2-captioner --load .
```
Requires `src/embedded_key.py` (copy `src/embedded_key.py.template`, paste your
Fireworks key). That file is gitignored by design and never committed.

## Run locally without Docker (for development)
```bash
# create your key file first:
cp src/embedded_key.py.template src/embedded_key.py   # then edit in your key
export TASKS_INPUT_PATH=./test_input/tasks.json
export RESULTS_OUTPUT_PATH=./test_output/results.json
python -m src.main
```

## Input / output format
Input `/input/tasks.json`: list of `{task_id, video_url, styles[]}`.
Output `/output/results.json`: list of `{task_id, captions{style: text}}`.

## Known limitations
- Music-only clips: captions rely on visual frames only (audio transcript is a
  planned enhancement).
- <add anything you discover during testing>

## License
MIT
=======
# track2-video-captioner
>>>>>>> 7c4162a2b24c3b50afd6d38fdc58a40af8822b91
