from __future__ import annotations

from typing import Any, Callable

Solver = Callable[..., dict[str, Any]]

_REGISTRY: dict[str, Solver] = {}


def register(*risk_types: str) -> Callable[[Solver], Solver]:
    def decorator(func: Solver) -> Solver:
        for risk_type in risk_types:
            _REGISTRY[risk_type] = func
        return func
    return decorator


def get(risk_type: str) -> Solver:
    try:
        return _REGISTRY[risk_type]
    except KeyError:
        raise NotImplementedError(
            f"risk_type {risk_type!r} is not supported "
            f"(available: {sorted(_REGISTRY)})"
        )


def available() -> list[str]:
    return sorted(_REGISTRY)
