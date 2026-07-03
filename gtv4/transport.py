from __future__ import annotations

import logging
import threading
import time
from typing import Any

from horaa_tls import Session

from . import settings

log = logging.getLogger(__name__)

TRANSPORT_ERRORS = (
    ConnectionError,
    OSError,
)


def build_session(proxy: str | None = None, verify: bool = True) -> Session:
    return Session(
        profile=settings.CLIENT_PROFILE,
        proxy=proxy,
        insecure_skip_verify=not verify,
    )


_local = threading.local()
_all_sessions: list[Session] = []
_lock = threading.Lock()


def cached_session(proxy: str | None = None, verify: bool = True) -> Session:
    cache = getattr(_local, "sessions", None)
    if cache is None:
        cache = _local.sessions = {}

    key = (proxy, verify)
    entry = cache.get(key)
    now = time.monotonic()

    if entry is None or (now - entry[1]) > settings.SESSION_TTL:
        if entry is not None:
            log.info("cached session expired (age=%.1fs, ttl=%s), invalidating",
                     now - entry[1], settings.SESSION_TTL)
            try:
                entry[0].close()
            except Exception:
                pass
            with _lock:
                try:
                    _all_sessions.remove(entry[0])
                except ValueError:
                    pass
        session = build_session(proxy=proxy, verify=verify)
        cache[key] = (session, now)
        with _lock:
            _all_sessions.append(session)
        return session

    return entry[0]


def invalidate_session(proxy: str | None = None, verify: bool = True) -> None:
    cache = getattr(_local, "sessions", None)
    if cache is None:
        return

    key = (proxy, verify)
    entry = cache.pop(key, None)
    if entry is not None:
        try:
            entry[0].close()
        except Exception:
            pass
        with _lock:
            try:
                _all_sessions.remove(entry[0])
            except ValueError:
                pass


def close_all() -> None:
    with _lock:
        for session in _all_sessions:
            try:
                session.close()
            except Exception:
                pass
        _all_sessions.clear()


def get_with_retry(session, url: str, retries: int = 2, backoff: float = 0.5, **kwargs) -> Any:
    for attempt in range(retries + 1):
        try:
            return session.get(url, **kwargs)
        except TRANSPORT_ERRORS as exc:
            if attempt == retries:
                log.warning("GET request failed after %d retries: %s", retries, exc)
                raise
            sleep_time = backoff * (2 ** attempt)
            log.info("GET transport error (%s) on attempt %d; retrying in %.2fs...",
                     exc, attempt + 1, sleep_time)
            time.sleep(sleep_time)
