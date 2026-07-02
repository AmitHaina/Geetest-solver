"""
Lot-number derivation.

Geetest embeds a dynamic key/value entry in the payload that is built by
picking specific characters out of ``lot_number``. The selection rule is a
constant extracted from the client script (see ``settings.LOT_MAPPING``).

A term looks like ``n[a:b]+n[c:d]`` where each ``n[a:b]`` contributes
``lot_number[a:b+1]`` (inclusive end) and ``+`` concatenates them.
"""

from __future__ import annotations

import re

from . import settings

_TERM = re.compile(r"n\[(\d+):(\d+)\]")


def _expand(spec: str, lot_number: str) -> str:
    parts = []
    for start, end in _TERM.findall(spec):
        start, end = int(start), int(end)
        if end >= len(lot_number):
            raise ValueError(
                f"lot_number too short: term n[{start}:{end}] needs length "
                f"{end + 1}, got {len(lot_number)}"
            )
        parts.append(lot_number[start: end + 1])
    return "".join(parts)


def build_lot_entry(
    lot_number: str,
    mapping: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return the ``{derived_key: derived_value}`` entry for ``lot_number``."""
    mapping = mapping or settings.LOT_MAPPING
    return {
        _expand(key_spec, lot_number): _expand(value_spec, lot_number)
        for key_spec, value_spec in mapping.items()
    }
