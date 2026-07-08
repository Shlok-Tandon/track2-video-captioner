"""Resolve the Fireworks API key and base URL.

Priority: environment variable first (local dev, and future-proof if the
organizers ever announce they inject one), then the embedded key baked into
the image. A fresh clone without embedded_key.py still runs if the teammate
uses their own .env / env var.
"""
import os

try:
    from .embedded_key import EMBEDDED_FIREWORKS_KEY
except ImportError:  # clone without the key file (e.g. teammate using .env)
    EMBEDDED_FIREWORKS_KEY = ""

BASE_URL = os.environ.get(
    "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
)


def get_api_key() -> str:
    key = os.environ.get("FIREWORKS_API_KEY") or EMBEDDED_FIREWORKS_KEY
    if not key:
        raise RuntimeError(
            "No Fireworks key found. Set the FIREWORKS_API_KEY environment "
            "variable, or create src/embedded_key.py from the template."
        )
    return key
