"""GoTrue JWT verification.

Supabase signs access tokens with HS256 using the project's JWT secret. We only
need to confirm the signature and pull out ``sub`` (the caregiver id) and
``exp``; PostgREST does the real authorization via RLS when we hand it the raw
token.
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt

from app.config import Settings


@dataclass(frozen=True, slots=True)
class TokenClaims:
    sub: str
    exp: int
    email: str | None


class InvalidTokenError(Exception):
    pass


def verify_access_token(token: str, settings: Settings) -> TokenClaims:
    if not settings.supabase_jwt_secret:
        raise RuntimeError("SUPABASE_JWT_SECRET is not configured")
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as e:
        raise InvalidTokenError(str(e)) from e
    return TokenClaims(sub=payload["sub"], exp=int(payload["exp"]), email=payload.get("email"))
