"""Secret handling: symmetric encryption for stored tokens, argon2 for the PIN.

- Supabase access/refresh tokens are encrypted with Fernet before they touch the
  database (``SESSION_TOKEN_ENC_KEY``), so a DB dump never yields a live session.
- The Caregiver-Mode PIN is hashed with argon2id and an optional server pepper.
  ``pin_hash`` is never returned by any endpoint.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.config import Settings

_ph = PasswordHasher()


def _fernet(settings: Settings) -> Fernet:
    if not settings.session_token_enc_key:
        raise RuntimeError("SESSION_TOKEN_ENC_KEY is not configured")
    return Fernet(settings.session_token_enc_key.encode())


def encrypt(value: str, settings: Settings) -> str:
    return _fernet(settings).encrypt(value.encode()).decode()


def decrypt(token: str, settings: Settings) -> str:
    try:
        return _fernet(settings).decrypt(token.encode()).decode()
    except InvalidToken as e:  # rotated key, tampering, corruption
        raise ValueError("could not decrypt stored token") from e


def hash_pin(pin: str, settings: Settings) -> str:
    return _ph.hash(pin + settings.pin_pepper)


def verify_pin(pin_hash: str, pin: str, settings: Settings) -> bool:
    try:
        _ph.verify(pin_hash, pin + settings.pin_pepper)
        return True
    except VerifyMismatchError:
        return False


def pin_needs_rehash(pin_hash: str) -> bool:
    return _ph.check_needs_rehash(pin_hash)
