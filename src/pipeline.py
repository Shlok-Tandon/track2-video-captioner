@'
"""Two-stage captioning: describe the video, then restyle into 4 tones.

Stage A (describe) targets the judge's ACCURACY axis.
Stage B (restyle) targets the judge's STYLE-MATCH axis.
Keeping them separate lets you tune each independently.
"""
import json
import os
import re

from .fireworks_client import chat, b64_image

DESCRIBE_MODEL = os.environ.get(
    "DESCRIBE_MODEL", "accounts/fireworks/models/kimi-k2p6")
RESTYLE_MODEL = os.environ.get(
    "RESTYLE_MODEL", "accounts/fireworks/models/gpt-oss-120b")
FALLBACK_MODEL = os.environ.get(
    "FALLBACK_MODEL", "accounts/fireworks/models/kimi-k2p5")

NO_REASONING_SYSTEM = (
    "Answer directly and concisely. Do not show your reasoning, do not "
    "think step by step out loud, and do not add any preamble or "
    "explanation - output only the final answer requested."
)

STYLE_DEFINITIONS = {
    "formal": (
        "professional, objective, factual tone; one complete grammatical "
        "sentence, up to 30 words; no humour, no opinion"),
    "sarcastic": (
        "dry, ironic, lightly mocking; ONE short punchy sentence, ideally "
        "under 20 words - a single clean jab, not an explanation; still "
        "clearly grounded in what is actually in the video"),
    "humorous_tech": (
        "funny, built on technology/programming metaphors (code, servers, "
        "networking, software terms); SHORT and punchy - 1-2 short "
        "sentences, under 25 words total, landing on a clear punchline "
        "rather than describing the scene at length; must contain at "
        "least one clear tech reference"),
    "humorous_non_tech": (
        "funny, everyday humour anyone would get; SHORT and punchy - 1-2 "
        "short sentences, under 25 words total, landing on a clear "
        "punchline rather than describing the scene at length; absolutely "
        "zero technology or programming references"),
}

SAFE_FALLBACK = {
    "formal": "A short video clip depicting a scene of everyday activity.",
    "sarcastic": "Oh, riveting stuff happening in this clip, truly.",
    "humorous_tech": "404: witty caption not found, but the video runs fine.",
    "humorous_non_tech": "Just your average clip, doing its best out there.",
}

_SENTENCE_END = re.compile(r"[.!?][\"')\]]?\s*$")
HUMOUR_STYLES = ("humorous_tech", "humorous_non_tech")
_MAX_HUMOUR_WORDS = 30


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


def _trim_to_complete_sentence(text: str) -> str:
    text = text.strip()
    if not text or _SENTENCE_END.search(text):
        return text
    last = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
    if last > 40:
        return text[: last + 1]
    clause = max(text.rfind(","), text.rfind(";"))
    if clause > 40:
        return text[:clause].rstrip() + "."
    return text.rstrip(" ,;:") + "."


def describe_scene(frame_paths: list) -> str:
    content = [{"type": "text", "text": (
        "Describe factually and neutrally what is happening in this video, "
        "based on these sampled frames in order. Cover the setting, the "
        "main subjects, their appearance, and the key actions or motion "
        "across the frames, in 2-4 complete sentences. Mention colours and "
        "notable objects, and use ONE consistent, specific, precise term "
        "for each object you name - never call the same object by two "
        "different names within the description if it could be described "
        "more than one way. If a recognizable city, landmark, or specific "
        "location is clearly identifiable from the visuals, name it "
        "explicitly; otherwise describe the setting generically. No "
        "opinion, no tone, no speculation about things not visible. Every "
        "sentence must be complete - never stop mid-sentence. Output ONLY "
        "the description itself.")}]
    for fp in frame_paths:
        content.append({"type": "image_url", "image_url": {
            "url": f"data:image/jpeg;base64,{b64_image(fp)}"}})
    messages = [
        {"role": "system", "content": NO_REASONING_SYSTEM},
        {"role": "user", "content": content},
    ]
    try:
        raw = chat(DESCRIBE_MODEL, messages, max_tokens=600,
                   reasoning_effort="low")
    except Exception:
        raw = chat(FALLBACK_MODEL, messages, max_tokens=600,
                   reasoning_effort="low")
    return _trim_to_complete_sentence(_clean_text(raw))


def _valid_captions(parsed: dict, requested_styles: list) -> bool:
    for s in requested_styles:
        v = parsed.get(s)
        if not isinstance(v, str) or len(v.strip()) < 15:
            return False
        if not _SENTENCE_END.search(v.strip()):
            return False
        if s in HUMOUR_STYLES and len(v.strip().split()) > _MAX_HUMOUR_WORDS:
            return False
    return True


def restyle(description: str, requested_styles: list) -> dict:
    style_lines = "\n".join(
        f'- "{s}": {STYLE_DEFINITIONS[s]}' for s in requested_styles)
    keys = json.dumps(requested_styles)
    prompt = (
        "Rewrite this factual video description as one caption per style. "
        "Favor short, punchy captions over long descriptive ones - the "
        "humorous styles especially should read like a quick joke with a "
        "clean landing, not a restated description with a joke bolted on.\n"
        "Rules for every caption:\n"
        "- follow each style's own length limit exactly (see below)\n"
        "- grounded ONLY in the description; invent no new objects, names, "
        "numbers, or details not stated there\n"
        "- use the EXACT SAME term for each object as the description uses "
        "- do not swap in a synonym or a different guess at what it is\n"
        "- each style must sound clearly different from the others\n\n"
        f'Description: "{description}"\n\n'
        f"Styles:\n{style_lines}\n\n"
        f"Return ONLY a JSON object with exactly these keys: {keys}. "
        "No markdown fences, no extra text, no reasoning - the JSON object "
        "must be your entire response.")
    messages = [
        {"role": "system", "content": NO_REASONING_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    best = {}
    for model in (RESTYLE_MODEL, FALLBACK_MODEL):
        try:
            raw = chat(model, messages, max_tokens=900,
                       reasoning_effort="low")
            parsed = _extract_json(raw)
            if _valid_captions(parsed, requested_styles):
                return parsed
            if parsed and len(parsed) > len(best):
                best = parsed
        except Exception:
            continue
    return best


def caption_clip(frame_paths: list, requested_styles: list) -> dict:
    description = describe_scene(frame_paths)
    captions = restyle(description, requested_styles)
    for style in requested_styles:
        val = captions.get(style)
        if not isinstance(val, str) or not val.strip():
            captions[style] = SAFE_FALLBACK.get(style, "A short video clip.")
        else:
            captions[style] = _trim_to_complete_sentence(val.strip())
    return {s: captions[s] for s in requested_styles}
'@ | Set-Content -Path src\pipeline.py -Encoding utf8