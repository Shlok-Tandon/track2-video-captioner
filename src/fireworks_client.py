"""Thin wrapper around the Fireworks chat-completions endpoint."""
import base64
import time

import requests

from .config import get_api_key, BASE_URL


def b64_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def chat(model: str, messages: list,
         timeout: int = 25, max_tokens: int = 500) -> str:
    """Call chat-completions and return the assistant text. One retry."""
    last_err = None
    for attempt in range(2):
        try:
            resp = requests.post(
                f"{BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {get_api_key()}"},
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.6,
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise last_err
