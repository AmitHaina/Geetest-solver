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
    return secrets.token_hex(8)


def _aes_hex(plaintext: str, uid: str) -> str:
    cipher = AES.new(uid.encode("utf-8"), AES.MODE_CBC, settings.AES_IV)
    ciphertext = cipher.encrypt(pad(plaintext.encode("utf-8"), AES.block_size))
    return binascii.hexlify(ciphertext).decode()


def _rsa_hex(uid: str) -> str:
    return binascii.hexlify(_RSA.encrypt(uid.encode("utf-8"))).decode()


def encrypt_w(plaintext: str, pt: str) -> str:
    if not pt or pt == "0":
        return quote_plus(plaintext)

    if pt != "1":
        raise NotImplementedError(f"unsupported payload protocol pt={pt!r}")

    uid = _new_uid()
    return _aes_hex(plaintext, uid) + _rsa_hex(uid)
