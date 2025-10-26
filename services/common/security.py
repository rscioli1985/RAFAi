from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Final


ALGORITHM: Final = "pbkdf2_sha256"
ITERATIONS: Final = 390000
SALT_BYTES: Final = 16


def _b64_encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("utf-8")


def _b64_decode(encoded: str) -> bytes:
    return base64.b64decode(encoded.encode("utf-8"))


def hash_password(password: str) -> str:
    salt = os.urandom(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${_b64_encode(salt)}${_b64_encode(dk)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt_b64, hash_b64 = password_hash.split("$", 3)
        iterations = int(iterations_str)
    except ValueError:
        return False

    if algorithm != ALGORITHM:
        return False

    salt = _b64_decode(salt_b64)
    expected = _b64_decode(hash_b64)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)
