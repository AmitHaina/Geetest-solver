"""Small shared helpers."""

from __future__ import annotations

import json
import random
import time


def make_callback() -> str:
    """Build a JSONP callback name in the format Geetest expects."""
    return f"geetest_{int(random.random() * 10000) + int(time.time() * 1000)}"


def parse_jsonp(text: str, callback: str) -> dict:
    """Unwrap a ``callback({...})`` JSONP body into its JSON object."""
    marker = f"{callback}("
    start = text.find(marker)
    if start == -1:
        raise ValueError(f"response is not the expected JSONP: {text[:120]!r}")

    body = text[start + len(marker):].strip()
    if body.endswith(";"):
        body = body[:-1]
    if body.endswith(")"):
        body = body[:-1]

    return json.loads(body)
