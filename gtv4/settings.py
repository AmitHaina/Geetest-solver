import json
import os

API_HOST = "https://gcaptcha4.geevisit.com"
LOAD_PATH = "/load"
VERIFY_PATH = "/verify"

STATIC_HOST = "https://static.geetest.com"

CLIENT_PROFILE = os.getenv("GTV4_CLIENT_PROFILE", "chrome_133")

DEFAULT_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "no-cors",
    "sec-fetch-dest": "script",
}

RSA_MODULUS_HEX = (
    "00c1e3934d1614465b33053e7f48ee4ec87b14b95ef88947713d25eecbff7e74"
    "c7977d02dc1d9451f79dd5d1c10c29acb6a9b4d6fb7d0a0279b6719e1772565f"
    "09af627715919221aef91899cae08c0d686d748b20a3603be2318ca6bc2b5970"
    "6592a9219d0bf05c9f65023a21d2330807252ae0066d59ceefa5f2748ea80bab81"
)
RSA_EXPONENT_HEX = "10001"

AES_IV = b"0000000000000000"

LOT_MAPPING = json.loads(
    os.getenv(
        "GTV4_LOT_MAPPING",
        '{"n[20:20]+n[8:8]+n[11:11]+n[30:30]": "n[16:21]"}',
    )
)

STATIC_ABO = json.loads(
    os.getenv("GTV4_STATIC_ABO", '{"jCpk": "yZ7D"}')
)

STATIC_BIHT = os.getenv("GTV4_STATIC_BIHT", "1426265548")
STATIC_EP = os.getenv("GTV4_STATIC_EP", "123")

ENV_REPORT = json.loads(
    os.getenv(
        "GTV4_ENV_REPORT",
        '{"ph": 0, "cp": 0, "ek": "11", "wd": 1, "nt": 0, "si": 0, "sc": 0}'
    )
)

GEE_GUARD = json.loads(
    os.getenv(
        "GTV4_GEE_GUARD",
        '{"roe": {"auh": "3", "aup": "3", "cdc": "3", "egp": "3", "res": "3", "rew": "3", "sep": "3", "snh": "3"}}'
    )
)

SLIDE_SCALE = 1.0059466666666665
SLIDE_OFFSET = 2.0

SESSION_TTL = int(os.getenv("GTV4_SESSION_TTL", "1800"))
