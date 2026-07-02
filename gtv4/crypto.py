"""
Payload encryption — produces the ``w`` parameter.

For ``pt == "1"`` the scheme is:

    uid      = 16 random hex chars
    aes_part = AES-CBC(PKCS7(plaintext), key=uid, iv="0000000000000000")
    rsa_part = RSA/PKCS1v1.5(uid)              # server decrypts to recover uid
    w        = hex(aes_part) + hex(rsa_part)

For ``pt`` of ``0``/empty the plaintext is simply URL-encoded.
"""

from __future__ import annotations

import binascii
import secrets
from urllib.parse import quote_plus

from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey.RSA import construct
from Crypto.Util.Padding import pad

from . import settings

_PUBLIC_KEY = construct(
    (int(settings.RSA_MODULUS_HEX, 16), int(settings.RSA_EXPONENT_HEX, 16))
)
_RSA = PKCS1_v1_5.new(_PUBLIC_KEY)


def _new_uid() -> str:
    """A 16-hex-character session key."""
    return secrets.token_hex(8)


def _aes_hex(plaintext: str, uid: str) -> str:
    cipher = AES.new(uid.encode("utf-8"), AES.MODE_CBC, settings.AES_IV)
    ciphertext = cipher.encrypt(pad(plaintext.encode("utf-8"), AES.block_size))
    return binascii.hexlify(ciphertext).decode()


def _rsa_hex(uid: str) -> str:
    return binascii.hexlify(_RSA.encrypt(uid.encode("utf-8"))).decode()


def encrypt_w(plaintext: str, pt: str) -> str:
    """Encrypt the assembled payload into the ``w`` request parameter."""
    if not pt or pt == "0":
        return quote_plus(plaintext)

    if pt != "1":
        raise NotImplementedError(f"unsupported payload protocol pt={pt!r}")

    uid = _new_uid()
    return _aes_hex(plaintext, uid) + _rsa_hex(uid)
