"""
Proof-of-work.

Geetest asks the client to find a nonce so that
``hash(version|bits|hashfunc|datetime|captcha_id|lot_number||<nonce>)`` has a
given number of leading zero bits. We brute-force the nonce and return the
message/signature pair the verify step expects.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from typing import Callable

log = logging.getLogger(__name__)

_HASHES: dict[str, Callable] = {
    "md5": hashlib.md5,
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
}

# Safety cutoff so a broken/too-high difficulty can't spin forever.
_DEFAULT_DEADLINE = 30.0


def _build_prefix(challenge) -> str:
    detail = challenge.pow_detail
    fields = [
        str(detail["version"]),
        str(detail["bits"]),
        detail["hashfunc"],
        detail["datetime"],
        challenge.captcha_id,
        challenge.lot_number,
        "",  # unused field, kept empty by the protocol
    ]
    return "|".join(fields) + "|"


def solve(challenge, deadline: float = _DEFAULT_DEADLINE) -> dict[str, str]:
    """Return ``{"pow_msg", "pow_sign"}`` satisfying the challenge difficulty.

    Gives up after ``deadline`` seconds so an impossible difficulty can't hang
    the caller.
    """
    detail = challenge.pow_detail
    hashfunc = _HASHES[detail["hashfunc"]]
    difficulty = int(detail["bits"])
    prefix = _build_prefix(challenge)
    give_up_at = time.monotonic() + deadline

    started = time.perf_counter()
    attempts = 0
    while time.monotonic() < give_up_at:
        nonce = secrets.token_hex(8)
        candidate = prefix + nonce
        digest = hashfunc(candidate.encode("utf-8")).hexdigest()
        attempts += 1

        # Leading `difficulty` bits must be zero.
        if int(digest, 16) >> (len(digest) * 4 - difficulty) == 0:
            log.debug(
                "pow solved (bits=%d, hash=%s, attempts=%d, %.0fms)",
                difficulty, detail["hashfunc"], attempts,
                (time.perf_counter() - started) * 1000,
            )
            return {"pow_msg": candidate, "pow_sign": digest}

    log.warning("pow gave up (bits=%d, attempts=%d, %.1fs)",
                difficulty, attempts, deadline)
    raise TimeoutError(
        f"proof-of-work not solved within {deadline}s (bits={difficulty})"
    )
