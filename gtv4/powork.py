from __future__ import annotations

import atexit
import concurrent.futures
import hashlib
import logging
import os
import secrets
import threading
import time
from typing import Callable

log = logging.getLogger(__name__)

_HASHES: dict[str, Callable] = {
    "md5": hashlib.md5,
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
}

_DEFAULT_DEADLINE = 30.0

_PROCESS_POOL: concurrent.futures.ProcessPoolExecutor | None = None
_POOL_LOCK = threading.Lock()


def _get_process_pool() -> concurrent.futures.ProcessPoolExecutor:
    global _PROCESS_POOL
    with _POOL_LOCK:
        if _PROCESS_POOL is None:
            max_workers = os.cpu_count() or 2
            _PROCESS_POOL = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)
        return _PROCESS_POOL


def _shutdown_pool():
    global _PROCESS_POOL
    if _PROCESS_POOL is not None:
        _PROCESS_POOL.shutdown(wait=False)


atexit.register(_shutdown_pool)


def _build_prefix(challenge) -> str:
    detail = challenge.pow_detail
    fields = [
        str(detail["version"]),
        str(detail["bits"]),
        detail["hashfunc"],
        detail["datetime"],
        challenge.captcha_id,
        challenge.lot_number,
        "",
    ]
    return "|".join(fields) + "|"


def _pow_worker(prefix: str, hashfunc_name: str, difficulty: int, chunk_size: int, worker_id: int) -> dict[str, str] | None:
    import hashlib
    import secrets

    hashes = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha256": hashlib.sha256,
    }
    hashfunc = hashes[hashfunc_name]

    base_seed = secrets.token_hex(4)
    for i in range(chunk_size):
        nonce = f"{base_seed}{i:08x}"
        candidate = prefix + nonce
        digest = hashfunc(candidate.encode("utf-8")).hexdigest()

        if int(digest, 16) >> (len(digest) * 4 - difficulty) == 0:
            return {"pow_msg": candidate, "pow_sign": digest}
    return None


def solve(challenge, deadline: float = _DEFAULT_DEADLINE) -> dict[str, str]:
    detail = challenge.pow_detail
    hashfunc_name = detail["hashfunc"]
    difficulty = int(detail["bits"])
    prefix = _build_prefix(challenge)

    if difficulty <= 0:
        nonce = secrets.token_hex(8)
        candidate = prefix + nonce
        digest = _HASHES[hashfunc_name](candidate.encode("utf-8")).hexdigest()
        return {"pow_msg": candidate, "pow_sign": digest}

    pool = _get_process_pool()
    num_workers = os.cpu_count() or 2
    chunk_size = 50000

    started = time.perf_counter()
    give_up_at = time.monotonic() + deadline

    futures = {
        pool.submit(_pow_worker, prefix, hashfunc_name, difficulty, chunk_size, w_id): w_id
        for w_id in range(num_workers)
    }

    try:
        while futures and time.monotonic() < give_up_at:
            remaining_time = max(0.1, give_up_at - time.monotonic())
            done, not_done = concurrent.futures.wait(
                futures.keys(),
                timeout=min(0.2, remaining_time),
                return_when=concurrent.futures.FIRST_COMPLETED
            )

            for future in done:
                result = future.result()
                if result is not None:
                    for f in futures:
                        f.cancel()
                    log.debug(
                        "pow solved (bits=%d, hash=%s, time=%.0fms)",
                        difficulty, hashfunc_name, (time.perf_counter() - started) * 1000,
                    )
                    return result
                
                futures.pop(future)
                if time.monotonic() < give_up_at:
                    new_worker_id = len(futures) + 1
                    new_future = pool.submit(_pow_worker, prefix, hashfunc_name, difficulty, chunk_size, new_worker_id)
                    futures[new_future] = new_worker_id

    finally:
        for f in futures:
            f.cancel()

    log.warning("pow gave up (bits=%d, %.1fs)", difficulty, deadline)
    raise TimeoutError(
        f"proof-of-work not solved within {deadline}s (bits={difficulty})"
    )
