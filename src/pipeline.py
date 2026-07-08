"""Two-stage captioning: describe the video, then restyle into 4 tones.

Stage A (describe) targets the judge's ACCURACY axis.
Stage B (restyle) targets the judge's STYLE-MATCH axis.
Keeping them separate lets you tune each independently.
"""
import json
import os
import re

from .fireworks_client import chat, b64_image

# Confirm the exact hosted IDs on Discord at launch, then update these.
# They are env-overridable so you can A/B a fine-tuned model without editing code:
#   set RESTYLE_MODEL=accounts/<you>/models/<your-finetune>  and re-run.
DESCRIBE_MODEL = os.environ.get(
    "DESCRIBE_MODEL", "accounts/fireworks/models/<gemma-vision-id>")
RESTYLE_MODEL = os.environ.get(
    "RESTYLE_MODEL", "accounts/fireworks/models/<gemma-text-id>")
FALLBACK_MODEL = os.environ.get(
    "FALLBACK_MODEL", "accounts/fireworks/models/<non-gemma-backup-id>")

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
    """Tolerate markdown fences and prose around the JSON object."""
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return {}


def describe_scene(frame_paths: list) -> str:
    content = [{"type": "text", "text": (
        "Describe factually and neutrally what is happening in this video, "
        "based on these sampled frames in order. Cover setting, subjects and "
        "key actions in 2-4 sentences. No opinion, no tone, no speculation.")}]
    for fp in frame_paths:
        content.append({"type": "image_url", "image_url": {
            "url": f"data:image/jpeg;base64,{b64_image(fp)}"}})
    messages = [{"role": "user", "content": content}]
    try:
        return chat(DESCRIBE_MODEL, messages)
    except Exception:
        return chat(FALLBACK_MODEL, messages)


def restyle(description: str, requested_styles: list) -> dict:
    style_lines = "\n".join(
        f"- {s}: {STYLE_DEFINITIONS[s]}" for s in requested_styles)
    prompt = (
        "Rewrite this factual video description as one caption per style. "
        "Each caption: a single vivid sentence grounded ONLY in the "
        f"description.\n\nDescription: \"{description}\"\n\n"
        f"Styles:\n{style_lines}\n\n"
        "Return ONLY a JSON object with exactly these keys: "
        f"{requested_styles}. No markdown fences, no extra text.")
    messages = [{"role": "user", "content": prompt}]
    for model in (RESTYLE_MODEL, FALLBACK_MODEL):  # retry on the other model
        try:
            parsed = _extract_json(chat(model, messages))
            if parsed:
                return parsed
        except Exception:
            continue
    return {}


def caption_clip(frame_paths: list, requested_styles: list) -> dict:
    description = describe_scene(frame_paths)
    captions = restyle(description, requested_styles)
    for style in requested_styles:  # guarantee every requested key exists
        val = captions.get(style)
        if not isinstance(val, str) or not val.strip():
            captions[style] = SAFE_FALLBACK.get(style, "A short video clip.")
    return {s: captions[s] for s in requested_styles}
