# Track 2 Video Captioning Agent - 404 Found

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
  -> STAGE A  describe (vision model)   -> neutral factual description
  -> STAGE B  restyle  (text model)     -> ONE JSON object, all 4 styles
  -> validate: every style key present + non-empty + complete sentence?
               else repair or safe fallback
  -> results.json
```

Current model stack (Fireworks AI, env-overridable in `src/pipeline.py`):

- Stage A (describe / accuracy): `kimi-k2p6` vision, `kimi-k2p5` fallback
- Stage B (restyle / style-match): `gpt-oss-120b` text

A Gemma model (Gemma 4 E4B on Fireworks) is a planned enhancement for the
"Best Use of Gemma" prize; it is not wired in as the primary model at the time
of writing.

## Run it (the way the judge does)

```bash
docker pull ghcr.io/shlok-tandon/track2-captioner:latest
docker run --rm \
  -v "$(pwd)/test_input:/input" \
  -v "$(pwd)/test_output:/output" \
  ghcr.io/shlok-tandon/track2-captioner:latest
cat test_output/results.json
```

## Build from source

```bash
docker buildx build --platform linux/amd64 -t track2-captioner --load .
```

Requires `src/embedded_key.py` (copy `src/embedded_key.py.template`, paste your
Fireworks key). That file is gitignored by design and never committed. In CI the
key is injected from the `FIREWORKS_API_KEY` GitHub Actions secret.

## Run locally without Docker (for development)

```bash
# create your key file first:
cp src/embedded_key.py.template src/embedded_key.py   # then edit in your key
export TASKS_INPUT_PATH=./test_input/tasks.json
export RESULTS_OUTPUT_PATH=./test_output/results.json
python -m src.main
cat test_output/results.json
```

On Windows PowerShell, use `$env:TASKS_INPUT_PATH = ".\test_input\tasks.json"`
and `$env:RESULTS_OUTPUT_PATH = ".\test_output\results.json"` instead of
`export`.

## Input / output format

Input `/input/tasks.json`: a list of `{task_id, video_url, styles[]}`.
Output `/output/results.json`: a list of `{task_id, captions{style: text}}`.
A caption is produced for every requested style of every clip; a missing style
key would zero that clip's score, so the pipeline always fills a safe fallback
rather than omitting a key.

## Design notes

- Frames are downscaled to 512px wide: the example clips are UHD, and eight
  full-resolution frames base64-encoded would risk the 30s/request limit.
- One structured multi-style call (not four separate calls) keeps well inside
  the 30s/request and 10-minute total ceilings.
- Truncation repair trims a cut-off description back to its last complete
  sentence rather than shipping a broken fragment that would poison all four
  derived styles.

## Known limitations

- Music-only or silent clips are captioned from visual frames only (an audio
  transcript stage is a possible future enhancement).
- Broad-category testing beyond the official example clips is ongoing.

## License

MIT
