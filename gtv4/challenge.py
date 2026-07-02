"""
Challenge loading and parsing.

Wraps the ``/load`` call and exposes the fields the rest of the solver needs
through a small dataclass, keeping the raw payload available for anything else.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from . import settings, util

log = logging.getLogger(__name__)

# Fields every challenge must carry for the verify step to work.
_REQUIRED_FIELDS = ("lot_number", "process_token", "payload", "pt", "pow_detail")


@dataclass
class Challenge:
    """A parsed Geetest v4 challenge returned by ``/load``."""

    captcha_id: str
    risk_type: str
    raw: dict[str, Any]
    lang: str = "eng"

    @property
    def lot_number(self) -> str:
        return self.raw["lot_number"]

    @property
    def process_token(self) -> str:
        return self.raw["process_token"]

    @property
    def payload(self) -> str:
        return self.raw["payload"]

    @property
    def pt(self) -> str:
        return str(self.raw["pt"])

    @property
    def pow_detail(self) -> dict[str, Any]:
        return self.raw["pow_detail"]

    @property
    def captcha_type(self) -> str:
        return self.raw.get("captcha_type", self.risk_type)


def load_challenge(
    session,
    captcha_id: str,
    risk_type: str,
    lang: str = "eng",
    timeout: int = 15,
) -> Challenge:
    """Request a fresh challenge from ``/load`` and parse it."""
    callback = util.make_callback()
    params = {
        "captcha_id": captcha_id,
        "challenge": str(uuid.uuid4()),
        "client_type": "web",
        "risk_type": risk_type,
        "lang": lang,
        "callback": callback,
    }

    response = session.get(
        settings.API_HOST + settings.LOAD_PATH,
        params=params,
        headers=settings.DEFAULT_HEADERS,
        timeout=timeout,
    )

    envelope = util.parse_jsonp(response.text, callback)
    if envelope.get("status") != "success":
        log.warning("/load failed (captcha_id=%s): %s", captcha_id, envelope)
        raise RuntimeError(f"/load failed: {envelope}")

    data = envelope.get("data")
    if not isinstance(data, dict):
        log.warning("/load returned no data (captcha_id=%s): %s", captcha_id, envelope)
        raise RuntimeError(f"/load returned no challenge data: {envelope}")

    missing = [field for field in _REQUIRED_FIELDS if field not in data]
    if missing:
        log.warning("/load missing fields %s (captcha_id=%s)", missing, captcha_id)
        raise RuntimeError(f"/load response missing fields {missing}: {data}")

    pow_detail = data.get("pow_detail", {})
    log.debug(
        "loaded challenge (captcha_id=%s, risk=%s, lot=%s, pow_bits=%s, hash=%s)",
        captcha_id, risk_type, data.get("lot_number"),
        pow_detail.get("bits"), pow_detail.get("hashfunc"),
    )
    return Challenge(captcha_id=captcha_id, risk_type=risk_type, raw=data, lang=lang)
