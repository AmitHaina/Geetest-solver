from __future__ import annotations

import collections
import argparse
import atexit
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from flask import Flask, jsonify, request

from gtv4 import registry, solver, transport

app = Flask(__name__)
log = logging.getLogger("gtv4.api")

_SOLVE_TIMEOUT = 120.0

_POOL: ThreadPoolExecutor | None = None
_args: argparse.Namespace | None = None

_active_solves = 0
_solves_lock = threading.Lock()

_IP_LIMITS: dict[str, collections.deque] = collections.defaultdict(collections.deque)
_LIMITS_LOCK = threading.Lock()


def _is_rate_limited(ip: str, max_reqs: int, window: float) -> bool:
    now = time.monotonic()
    with _LIMITS_LOCK:
        timestamps = _IP_LIMITS[ip]
        while timestamps and now - timestamps[0] > window:
            timestamps.popleft()

        if len(_IP_LIMITS) > 1000:
            for key in list(_IP_LIMITS.keys()):
                old_ts = _IP_LIMITS[key]
                while old_ts and now - old_ts[0] > window:
                    old_ts.popleft()
                if not old_ts:
                    del _IP_LIMITS[key]

        if len(timestamps) >= max_reqs:
            return True
        timestamps.append(now)
        return False



def _solve(captcha_id: str, risk_type: str, proxy: str | None) -> dict:
    verify_tls = proxy is None
    session = transport.cached_session(proxy=proxy, verify=verify_tls)
    try:
        return solver.solve(
            captcha_id,
            risk_type,
            proxy=proxy,
            verify_tls=verify_tls,
            session=session,
        )
    except transport.TRANSPORT_ERRORS:
        log.warning("Solve failed due to transport error; invalidating cached session (proxy=%s)", bool(proxy))
        transport.invalidate_session(proxy=proxy, verify=verify_tls)
        raise



@app.post("/geetest")
def process_geetest():
    global _active_solves
    client_ip = request.remote_addr or "unknown"

    if _args and _args.ip_rate_limit_max > 0:
        if _is_rate_limited(client_ip, _args.ip_rate_limit_max, _args.ip_rate_limit_window):
            log.warning("Rate limit exceeded for IP %s", client_ip)
            return jsonify({
                "errorId": 1,
                "errorCode": "ERROR_TOO_MANY_REQUESTS",
                "errorDescription": f"Rate limit exceeded. Max {_args.ip_rate_limit_max} requests per {_args.ip_rate_limit_window}s.",
            }), 429

    if _args:
        queue_limit = _args.queue_limit if _args.queue_limit is not None else _args.threads
        max_allowed = _args.threads + queue_limit
        with _solves_lock:
            if _active_solves >= max_allowed:
                log.warning("Queue capacity reached. Rejecting request from %s (%d active solves)", client_ip, _active_solves)
                return jsonify({
                    "errorId": 1,
                    "errorCode": "ERROR_SERVER_BUSY",
                    "errorDescription": "Server is busy; queue capacity reached.",
                }), 429
            _active_solves += 1

    try:
        payload = request.get_json(silent=True) or {}
        captcha_id = payload.get("captcha_id")
        risk_type = payload.get("risk_type", "slide")
        proxy = payload.get("proxy")

        if proxy is not None:
            if not isinstance(proxy, str):
                return jsonify({
                    "errorId": 1,
                    "errorCode": "ERROR_WRONG_PROXY",
                    "errorDescription": "'proxy' must be a string",
                }), 200

            valid_prefixes = ("http://", "https://", "socks5://", "socks5h://", "socks4://")
            if not proxy.lower().startswith(valid_prefixes):
                return jsonify({
                    "errorId": 1,
                    "errorCode": "ERROR_WRONG_PROXY",
                    "errorDescription": f"'proxy' must start with one of: {', '.join(valid_prefixes)}",
                }), 200

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
        except Exception as exc:
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
    finally:
        if _args:
            with _solves_lock:
                _active_solves -= 1


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
    parser.add_argument("--queue-limit", type=int, default=None,
                        help="max pending tasks in queue (default: same as threads)")
    parser.add_argument("--ip-rate-limit-max", type=int, default=5,
                        help="max requests per IP in the window (default: 5, 0 to disable)")
    parser.add_argument("--ip-rate-limit-window", type=int, default=60,
                        help="sliding rate limit window in seconds (default: 60)")
    parser.add_argument("--log-level", default="INFO",
                        help="DEBUG, INFO, WARNING, ERROR")
    return parser.parse_args()


def _shutdown() -> None:
    if _POOL is not None:
        _POOL.shutdown(wait=True)
    transport.close_all()


def main() -> None:
    global _POOL, _args
    args = parse_args()
    _args = args
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _POOL = ThreadPoolExecutor(max_workers=args.threads)
    atexit.register(_shutdown)
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()

