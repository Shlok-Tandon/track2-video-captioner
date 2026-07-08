"""Two-stage captioning: describe the video, then restyle into 4 tones.

Stage A (describe) targets the judge's ACCURACY axis.
Stage B (restyle) targets the judge's STYLE-MATCH axis.
Keeping them separate lets you tune each independently.
"""
import json
import os
import re

from .fireworks_client import chat, b64_image

# Confirmed available on this Fireworks account as of today (no Gemma yet -
# swap in the real Gemma ID here the moment Discord announces it).
#   kimi-k2p6 / kimi-k2p5 : chat + image input  -> used for the vision step
#   gpt-oss-120b          : chat, reasoning model -> used for the text step
DESCRIBE_MODEL = os.environ.get(
    "DESCRIBE_MODEL", "accounts/fireworks/models/kimi-k2p6")
RESTYLE_MODEL = os.environ.get(
    "RESTYLE_MODEL", "accounts/fireworks/models/gpt-oss-120b")
FALLBACK_MODEL = os.environ.get(
    "FALLBACK_MODEL", "accounts/fireworks/models/kimi-k2p5")

# Most currently-available models are reasoning-tuned and "think out loud"
# before answering. This system message + reasoning_effort="low" (Section
# below) keep that under control; _extract_json() below is also defensive
# in case some reasoning text still slips in around the JSON.
NO_REASONING_SYSTEM = (
    "Answer directly and concisely. Do not show your reasoning, do not "
    "think step by step out loud, and do not add any preamble or "
    "explanation - output only the final answer requested."
)

STYLE_DEFINITIONS = {
    "formal": "professional, objective, factual tone",
    "sarcastic": "dry, ironic, lightly mocking",
    "humorous_tech": "funny, uses technology/programming references",
    "humorous_non_tech": "funny, everyday humour, zero technical jargon",
}

SAFE_FALLBACK = {
    "formal": "A short video clip depicting a scene of everyday activity.",
    "sarcastic": "Oh, riveting stuff happening in this clip, truly.",
    "humorous_tech": "404: witty caption not found, but the video runs fine.",
    "humorous_non_tech": "Just your average clip, doing its best out there.",
}


def _extract_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return {}


def _clean_text(raw: str) -> str:
    raw = raw.strip()
    for marker in ("Final answer:", "Answer:", "Description:"):
        if marker in raw:
            raw = raw.split(marker)[-1].strip()
    return raw


def describe_scene(frame_paths: list) -> str:
    content = [{"type": "text", "text": (
        "Describe factually and neutrally what is happening in this video, "
        "based on these sampled frames in order. Cover setting, subjects and "
        "key actions in 2-4 sentences. No opinion, no tone, no speculation. "
        "Output ONLY the description itself.")}]
    for fp in frame_paths:
        content.append({"type": "image_url", "image_url": {
            "url": f"data:image/jpeg;base64,{b64_image(fp)}"}})
    messages = [
        {"role": "system", "content": NO_REASONING_SYSTEM},
        {"role": "user", "content": content},
    ]
    try:
        raw = chat(DESCRIBE_MODEL, messages, max_tokens=350, reasoning_effort="low")
    except Exception:
        raw = chat(FALLBACK_MODEL, messages, max_tokens=350, reasoning_effort="low")
    return _clean_text(raw)


def restyle(description: str, requested_styles: list) -> dict:
    style_lines = "\n".join(
        f"- {s}: {STYLE_DEFINITIONS[s]}" for s in requested_styles)
    prompt = (
        "Rewrite this factual video description as one caption per style. "
        "Each caption: a single vivid sentence grounded ONLY in the "
        f"description.\n\nDescription: \"{description}\"\n\n"
        f"Styles:\n{style_lines}\n\n"
        "Return ONLY a JSON object with exactly these keys: "
        f"{requested_styles}. No markdown fences, no extra text, "
        "no reasoning - the JSON object must be your entire response.")
    messages = [
        {"role": "system", "content": NO_REASONING_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    for model in (RESTYLE_MODEL, FALLBACK_MODEL):
        try:
            raw = chat(model, messages, max_tokens=700, reasoning_effort="low")
            parsed = _extract_json(raw)
            if parsed:
                return parsed
        except Exception:
            continue
    return {}


def caption_clip(frame_paths: list, requested_styles: list) -> dict:
    description = describe_scene(frame_paths)
    captions = restyle(description, requested_styles)
    for style in requested_styles:
        val = captions.get(style)
        if not isinstance(val, str) or not val.strip():
            captions[style] = SAFE_FALLBACK.get(style, "A short video clip.")
    return {s: captions[s] for s in requested_styles}
