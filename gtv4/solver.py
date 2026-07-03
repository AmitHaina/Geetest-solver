from __future__ import annotations

import json
import logging
import time
from typing import Any

from . import payload as payload_mod
from . import challenge as challenge_mod
from . import crypto, registry, settings, transport, util
from . import slide # noqa: F401

log = logging.getLogger(__name__)


def _solve_challenge(session, challenge, timeout: int) -> dict[str, Any]:
    solver = registry.get(challenge.risk_type)
    return solver(session, challenge, timeout=timeout)


def verify(session, challenge, solution: dict[str, Any], timeout: int = 15) -> dict[str, Any]:
    base = payload_mod.build(challenge, solution)
    w = crypto.encrypt_w(json.dumps(base), challenge.pt)

    callback = util.make_callback()
    params = {
        "callback": callback,
        "captcha_id": challenge.captcha_id,
        "client_type": "web",
        "lot_number": challenge.lot_number,
        "risk_type": challenge.risk_type,
        "payload": challenge.payload,
        "process_token": challenge.process_token,
        "payload_protocol": "1",
        "pt": challenge.pt,
        "w": w,
    }

    started = time.perf_counter()
    response = transport.get_with_retry(
        session,
        settings.API_HOST + settings.VERIFY_PATH,
        params=params,
        headers=settings.DEFAULT_HEADERS,
        timeout=timeout,
    )
    elapsed = time.perf_counter() - started

    envelope = util.parse_jsonp(response.text, callback)
    if envelope.get("status") != "success":
        log.warning("verify rejected (lot=%s, %.0fms): %s",
                    challenge.lot_number, elapsed * 1000, envelope)
        raise RuntimeError(f"/verify failed: {envelope}")

    data = envelope["data"]
    if data.get("seccode") is None:
        log.warning("verify returned no seccode (lot=%s): %s",
                    challenge.lot_number, data)
        raise RuntimeError(f"/verify returned no seccode: {data}")

    log.info("verify ok (lot=%s, %.0fms)", challenge.lot_number, elapsed * 1000)
    return data["seccode"]


def solve(
    captcha_id: str,
    risk_type: str,
    proxy: str | None = None,
    verify_tls: bool = True,
    lang: str = "eng",
    timeout: int = 15,
    session=None,
) -> dict[str, Any]:
    own_session = session is None
    if own_session:
        session = transport.build_session(proxy=proxy, verify=verify_tls)
    try:
        t0 = time.perf_counter()
        challenge = challenge_mod.load_challenge(
            session, captcha_id, risk_type, lang=lang, timeout=timeout
        )
        t_load = time.perf_counter()

        solution = _solve_challenge(session, challenge, timeout)
        t_solve = time.perf_counter()

        seccode = verify(session, challenge, solution, timeout=timeout)
        t_verify = time.perf_counter()

        log.info(
            "solve done (captcha_id=%s, risk=%s) load=%.0fms challenge=%.0fms "
            "verify=%.0fms total=%.0fms",
            captcha_id, risk_type,
            (t_load - t0) * 1000, (t_solve - t_load) * 1000,
            (t_verify - t_solve) * 1000, (t_verify - t0) * 1000,
        )
        return seccode
    except Exception:
        log.exception("solve failed (captcha_id=%s, risk=%s)", captcha_id, risk_type)
        raise
    finally:
        if own_session:
            session.close()
