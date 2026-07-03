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
    mapping = mapping or settings.LOT_MAPPING
    return {
        _expand(key_spec, lot_number): _expand(value_spec, lot_number)
        for key_spec, value_spec in mapping.items()
    }
