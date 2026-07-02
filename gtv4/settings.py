"""
Protocol-level constants for Geetest v4.

These are facts about the wire format (endpoints, the server's public key,
the fixed AES IV). They are required for any client to interoperate with the
service and are not application logic.

The values most likely to drift when Geetest ships a new client script
(``CLIENT_PROFILE`` and ``LOT_MAPPING``) can be overridden at runtime via
environment variables, so a break can be patched without editing this file:

    GTV4_CLIENT_PROFILE=chrome_120
    GTV4_LOT_MAPPING='{"n[20:20]+n[8:8]+n[11:11]+n[30:30]": "n[16:21]"}'
"""

import json
import os

# --- Endpoints -------------------------------------------------------------

API_HOST = "https://gcaptcha4.geevisit.com"
LOAD_PATH = "/load"
VERIFY_PATH = "/verify"

# Host that serves the slide background / puzzle images.
STATIC_HOST = "https://static.geetest.com"

# --- Browser emulation (horaa-tls) -----------------------------------------

# Horaa TLS profile to emulate. The library keeps the TLS/JA3 signature,
# HTTP/2 settings, User-Agent and Client Hints aligned for this profile, so we
# do not set those headers by hand. Override with GTV4_CLIENT_PROFILE.
CLIENT_PROFILE = os.getenv("GTV4_CLIENT_PROFILE", "chrome_133")

# Request-context headers that are specific to how the Geetest script is loaded
# (the profile-aligned ones like user-agent / sec-ch-ua are added by horaa-tls).
DEFAULT_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "no-cors",
    "sec-fetch-dest": "script",
}

# --- Cryptography ----------------------------------------------------------

# The Geetest server's RSA public key used to wrap the per-request AES key.
RSA_MODULUS_HEX = (
    "00c1e3934d1614465b33053e7f48ee4ec87b14b95ef88947713d25eecbff7e74"
    "c7977d02dc1d9451f79dd5d1c10c29acb6a9b4d6fb7d0a0279b6719e1772565f"
    "09af627715919221aef91899cae08c0d686d748b20a3603be2318ca6bc2b5970"
    "6592a9219d0bf05c9f65023a21d2330807252ae0066d59ceefa5f2748ea80bab81"
)
RSA_EXPONENT_HEX = "10001"

# AES-CBC uses a fixed, all-zero-ascii IV in this protocol.
AES_IV = b"0000000000000000"

# --- Challenge-derived constants -------------------------------------------

# Rule for deriving the dynamic "lot" entry from lot_number, extracted from
# Geetest's obfuscated client script. Each ``n[a:b]`` selects lot_number[a:b+1];
# terms joined by "+" are concatenated. Re-derive this if the solver breaks, or
# override at runtime with GTV4_LOT_MAPPING (a JSON object).
LOT_MAPPING = json.loads(
    os.getenv(
        "GTV4_LOT_MAPPING",
        '{"n[20:20]+n[8:8]+n[11:11]+n[30:30]": "n[16:21]"}',
    )
)

# --- Static payload fields -------------------------------------------------

# A fixed key/value pair from the client script (changes between JS versions).
STATIC_ABO = {"jCpk": "yZ7D"}

# Other fixed scalars embedded in the payload.
STATIC_BIHT = "1426265548"
STATIC_EP = "123"

# Environment self-report ("em"). Values below are what a clean desktop Chrome
# reports: no automation markers, error-keys bitmask 0x11, webdriver on proto.
ENV_REPORT = {
    "ph": 0,   # PhantomJS
    "cp": 0,   # callPhantom
    "ek": "11",  # Error-key bitmask (Chrome: message+stack)
    "wd": 1,   # navigator.webdriver present but not own-getter
    "nt": 0,   # Nightmare.js
    "si": 0,   # selenium script fn
    "sc": 0,   # selenium cdc marker
}

# gee_guard "roe" self-report; "3" means the anti-bot check passed.
GEE_GUARD = {
    "roe": {
        "auh": "3",  # headless UA
        "aup": "3",  # phantom UA
        "cdc": "3",  # cdc marker
        "egp": "3",  # phantom language
        "res": "3",  # selenium driver
        "rew": "3",  # webdriver
        "sep": "3",  # phantom properties
        "snh": "3",  # headless permissions
    }
}

# --- Slide geometry --------------------------------------------------------

# Converts the detected pixel offset into the value Geetest validates.
# SLIDE_SCALE == 0.8876 * 340 / 300
SLIDE_SCALE = 1.0059466666666665
SLIDE_OFFSET = 2.0
