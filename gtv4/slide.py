"""
Slide challenge solver.

Downloads the background and puzzle-piece images, locates the gap with edge
based template matching, and returns the ``setLeft`` / ``passtime`` /
``userresponse`` fields the slide payload needs.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import cv2
import numpy as np

from . import settings
from .registry import register

log = logging.getLogger(__name__)

_ALPHA_THRESHOLD = 10

# Below this the edge template match is essentially noise -> likely a missed
# gap. Correct matches on these images score ~0.26-0.40, so 0.15 only trips on
# genuine detection failures rather than crying wolf on good solves.
_MATCH_WARN_THRESHOLD = 0.15


def _decode(data: bytes, flags: int) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(data, np.uint8), flags)


def _fetch(session, path: str, timeout: int) -> bytes:
    url = f"{settings.STATIC_HOST}/{path}"
    return session.get(url, timeout=timeout).content


def _find_offset(background: np.ndarray, piece_rgba: np.ndarray) -> tuple[int, float]:
    """Return ``(travel_distance, match_score)`` in background pixels."""
    # Crop the visible piece out of its padded canvas using the alpha channel.
    alpha = piece_rgba[:, :, 3]
    ys, xs = np.where(alpha > _ALPHA_THRESHOLD)
    left, right = int(xs.min()), int(xs.max())
    top, bottom = int(ys.min()), int(ys.max())
    piece = piece_rgba[top: bottom + 1, left: right + 1, :3]

    # Match on edges so lighting/colour differences don't matter.
    bg_edges = cv2.Canny(background, 100, 200)
    piece_edges = cv2.Canny(piece, 100, 200)
    scores = cv2.matchTemplate(bg_edges, piece_edges, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(scores)

    # The piece starts with its left edge at `left` inside the canvas, so the
    # travel distance is the matched gap position minus that initial offset.
    return max_loc[0] - left, float(max_val)


@register("slide")
def solve(session, challenge, timeout: int = 15) -> dict[str, Any]:
    """Solve a slide challenge and return its payload fields."""
    t0 = time.perf_counter()
    background = _decode(_fetch(session, challenge.raw["bg"], timeout), cv2.IMREAD_COLOR)
    piece = _decode(_fetch(session, challenge.raw["slice"], timeout), cv2.IMREAD_UNCHANGED)
    download_ms = (time.perf_counter() - t0) * 1000

    if background is None or piece is None:
        log.warning("slide image decode failed (bg=%s, slice=%s)",
                    challenge.raw.get("bg"), challenge.raw.get("slice"))
        raise ValueError("failed to decode slide images (download failed or corrupt)")

    offset, score = _find_offset(background, piece)
    if score < _MATCH_WARN_THRESHOLD:
        log.warning("slide match weak (score=%.3f, offset=%d) — may be wrong",
                    score, offset)

    # Sub-pixel jitter: a pixel-perfect integer setLeft looks robotic, while
    # Geetest's slide check tolerates a few pixels of error. 0.0-0.5 stays well
    # inside that tolerance yet avoids submitting a suspiciously exact value.
    set_left = offset + random.uniform(0.0, 0.5)

    log.debug("slide solved (offset=%d, score=%.3f, download=%.0fms)",
              offset, score, download_ms)

    return {
        "setLeft": set_left,
        "passtime": random.randint(600, 1200),
        "userresponse": set_left / settings.SLIDE_SCALE + settings.SLIDE_OFFSET,
    }
