"""
Payload assembly.

Builds the plaintext object that gets encrypted into ``w``. It combines the
proof-of-work result, the lot-derived entry, the static anti-bot fields, and
the risk-type specific solution (e.g. the slide position).
"""

from __future__ import annotations

import copy
from typing import Any

from . import lot, powork, settings


def build(challenge, solution: dict[str, Any]) -> dict[str, Any]:
    """Assemble the payload dict for a solved ``challenge``.

    ``solution`` carries the risk-type specific fields (for slide:
    ``setLeft``, ``passtime``, ``userresponse``).
    """
    pow_result = powork.solve(challenge)

    return {
        **settings.STATIC_ABO,
        **pow_result,
        **lot.build_lot_entry(challenge.lot_number),
        "biht": settings.STATIC_BIHT,
        "device_id": "",
        "em": dict(settings.ENV_REPORT),
        "gee_guard": copy.deepcopy(settings.GEE_GUARD),
        "ep": settings.STATIC_EP,
        "geetest": "captcha",
        "lang": challenge.lang,
        "lot_number": challenge.lot_number,
        **solution,
    }
