"""
HTTP transport.

Thin wrapper around horaa-tls that gives us a session pre-configured to look
like a real Chrome browser (TLS/JA3 + HTTP/2 + aligned Client Hints).
"""

from __future__ import annotations

import threading

from horaa_tls import Session

from . import settings


def build_session(proxy: str | None = None, verify: bool = True) -> Session:
    """Create a browser-emulating Horaa TLS session for talking to Geetest."""
    return Session(
        profile=settings.CLIENT_PROFILE,
        proxy=proxy,
        insecure_skip_verify=not verify,
    )


# --- Optional per-thread session caching -----------------------------------
# Reusing a session keeps its underlying connection pool alive across solves.
# Sessions are cached per thread so concurrent workers never share one (horaa
# sessions are not meant to be used from multiple threads at once).

_local = threading.local()
_all_sessions: list[Session] = []
_lock = threading.Lock()


def cached_session(proxy: str | None = None, verify: bool = True) -> Session:
    """Return a thread-local session for ``(proxy, verify)``, creating once."""
    cache = getattr(_local, "sessions", None)
    if cache is None:
        cache = _local.sessions = {}

    key = (proxy, verify)
    session = cache.get(key)
    if session is None:
        session = build_session(proxy=proxy, verify=verify)
        cache[key] = session
        with _lock:
            _all_sessions.append(session)
    return session


def close_all() -> None:
    """Close every cached session (call on shutdown)."""
    with _lock:
        for session in _all_sessions:
            try:
                session.close()
            except Exception:
                pass
        _all_sessions.clear()

