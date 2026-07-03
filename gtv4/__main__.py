from __future__ import annotations

import json
import sys

from . import solver

_DEMO_CAPTCHA_ID = "54088bb07d2df3c46b79f80300b0abbe"
_DEMO_RISK_TYPE = "slide"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    captcha_id = argv[0] if len(argv) > 0 else _DEMO_CAPTCHA_ID
    risk_type = argv[1] if len(argv) > 1 else _DEMO_RISK_TYPE
    proxy = argv[2] if len(argv) > 2 else None

    seccode = solver.solve(
        captcha_id,
        risk_type,
        proxy=proxy,
        verify_tls=proxy is None,
    )
    print(json.dumps(seccode, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
