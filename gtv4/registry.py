"""
Solver registry.

Risk-type solvers register themselves with ``@register("slide")`` so new
challenge types can be added by dropping in a module and decorating its solve
function — no central dispatch table to edit.
"""

from __future__ import annotations

from typing import Any, Callable

Solver = Callable[..., dict[str, Any]]

_REGISTRY: dict[str, Solver] = {}


def register(*risk_types: str) -> Callable[[Solver], Solver]:
    """Register a solve function for one or more risk types."""
    def decorator(func: Solver) -> Solver:
        for risk_type in risk_types:
            _REGISTRY[risk_type] = func
        return func
    return decorator


def get(risk_type: str) -> Solver:
    """Return the solver for ``risk_type`` or raise ``NotImplementedError``."""
    try:
        return _REGISTRY[risk_type]
    except KeyError:
        raise NotImplementedError(
            f"risk_type {risk_type!r} is not supported "
            f"(available: {sorted(_REGISTRY)})"
        )


def available() -> list[str]:
    """List the registered risk types."""
    return sorted(_REGISTRY)
