"""
HTTP API for the Geetest v4 solver.

Mirrors the response shape of the Turnstile API so it can be used the same way.

    POST /geetest      {"captcha_id": "...", "risk_type": "slide", "proxy": null}
                       -> solves and returns the seccode

    GET  /             -> usage docs

Run:  python api_solver.py --host 0.0.0.0 --port 5000 --threads 4
"""

from __future__ import annotations

import argparse
import atexit
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from flask import Flask, jsonify, request

from gtv4 import registry, solver, transport

app = Flask(__name__)
log = logging.getLogger("gtv4.api")

# Hard cap on how long a single solve may run before the request gives up.
_SOLVE_TIMEOUT = 120.0

_POOL: ThreadPoolExecutor | None = None


def _solve(captcha_id: str, risk_type: str, proxy: str | None) -> dict:
    # Reuse a per-worker-thread session so its connection pool survives across
    # requests instead of dialing a fresh TLS connection every solve.
    session = transport.cached_session(proxy=proxy, verify=proxy is None)
    return solver.solve(
        captcha_id,
        risk_type,
        proxy=proxy,
        verify_tls=proxy is None,
        session=session,
    )


@app.post("/geetest")
def process_geetest():
    payload = request.get_json(silent=True) or {}
    captcha_id = payload.get("captcha_id")
    risk_type = payload.get("risk_type", "slide")
    proxy = payload.get("proxy")

    if not captcha_id:
        return jsonify({
            "errorId": 1,
            "errorCode": "ERROR_WRONG_CAPTCHA_ID",
            "errorDescription": "'captcha_id' is required",
        }), 200

    if not isinstance(captcha_id, str):
        return jsonify({
            "errorId": 1,
            "errorCode": "ERROR_WRONG_CAPTCHA_ID",
            "errorDescription": "'captcha_id' must be a string",
        }), 200

    if risk_type not in registry.available():
        return jsonify({
            "errorId": 1,
            "errorCode": "ERROR_WRONG_RISK_TYPE",
            "errorDescription": f"unsupported risk_type; available: {registry.available()}",
        }), 200

    log.info("solve request (captcha_id=%s, risk=%s, proxy=%s)",
             captcha_id, risk_type, bool(proxy))
    started = time.perf_counter()
    try:
        seccode = _POOL.submit(_solve, captcha_id, risk_type, proxy).result(
            timeout=_SOLVE_TIMEOUT
        )
    except FuturesTimeout:
        log.warning("solve timeout (captcha_id=%s) after %.1fs",
                    captcha_id, _SOLVE_TIMEOUT)
        return jsonify({
            "errorId": 1,
            "errorCode": "ERROR_CAPTCHA_TIMEOUT",
            "errorDescription": f"solve exceeded {_SOLVE_TIMEOUT}s",
        }), 200
    except Exception as exc:  # surface the failure through the API
        log.warning("solve failed (captcha_id=%s, %.0fms): %s",
                    captcha_id, (time.perf_counter() - started) * 1000, exc)
        return jsonify({
            "errorId": 1,
            "errorCode": "ERROR_CAPTCHA_UNSOLVABLE",
            "errorDescription": str(exc),
        }), 200

    log.info("solve ok (captcha_id=%s, %.0fms)",
             captcha_id, (time.perf_counter() - started) * 1000)
    return jsonify({
        "errorId": 0,
        "status": "ready",
        "solution": seccode,
    }), 200


@app.get("/")
def index():
    return jsonify({
        "service": "Geetest v4 Solver API",
        "usage": {
            "endpoint": "/geetest",
            "method": "POST",
            "content_type": "application/json",
            "body": {
                "captcha_id": "The Geetest captcha_id",
                "risk_type": "Challenge type (default: slide)",
                "proxy": "Optional proxy URL",
            },
            "example": {
                "captcha_id": "54088bb07d2df3c46b79f80300b0abbe",
                "risk_type": "slide",
            },
        },
    }), 200


def parse_args():
    parser = argparse.ArgumentParser(description="Geetest v4 Solver API")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--threads", type=int, default=4, help="concurrent solves")
    parser.add_argument("--log-level", default="INFO",
                        help="DEBUG, INFO, WARNING, ERROR")
    return parser.parse_args()


def _shutdown() -> None:
    """Release the worker pool and cached sessions on exit."""
    if _POOL is not None:
        _POOL.shutdown(wait=True)
    transport.close_all()


def main() -> None:
    global _POOL
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _POOL = ThreadPoolExecutor(max_workers=args.threads)
    atexit.register(_shutdown)
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
