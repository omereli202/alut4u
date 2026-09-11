"""Session lifecycle: sign-up, sign-in, sign-out, and per-request resolution.

The browser holds only a signed cookie carrying a ``device_sessions`` row id.
That row holds the (encrypted) Supabase tokens. On each request we load the row,
refresh the access token if it is close to expiring, and hand the caller a
ready-to-use Supabase client bound to the caregiver's JWT — so RLS enforces
tenancy.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from app.auth import crypto
from app.auth.gotrue import AuthError, AuthSession, GoTrue
from app.config import Settings
from app.repositories import caregivers as caregivers_repo
from app.repositories import consent as consent_repo
from app.repositories import device_sessions as sessions_repo
from app.services.supabase_client import user_client

_REFRESH_SKEW = timedelta(seconds=60)


class SessionError(Exception):
    """Cookie present but unusable — caller should clear it and 401."""


@dataclass(slots=True)
class ResolvedSession:
    session_id: str
    caregiver_id: str
    access_token: str
    elevated_until: datetime | None
    _db: Any = None

    @property
    def db(self) -> Any:
        return self._db

    def is_elevated(self, now: datetime | None = None) -> bool:
        if self.elevated_until is None:
            return False
        return (now or datetime.now(UTC)) < self.elevated_until


# --- creation ---------------------------------------------------------------


def _persist_new_session(
    auth: AuthSession,
    settings: Settings,
    *,
    device_label: str | None,
    ua: str | None,
    ip: str | None,
) -> str:
    expires_at = datetime.now(UTC) + timedelta(seconds=auth.expires_in)
    row = sessions_repo.create(
        caregiver_id=auth.user_id,
        refresh_token_enc=crypto.encrypt(auth.refresh_token, settings),
        access_token_enc=crypto.encrypt(auth.access_token, settings),
        access_token_expires_at=expires_at,
        device_label=device_label,
        user_agent=ua,
        ip=ip,
    )
    return row["id"]


def sign_up(
    *,
    email: str,
    password: str,
    display_name: str,
    settings: Settings,
    ua: str | None = None,
    ip: str | None = None,
) -> tuple[str, dict]:
    gotrue = GoTrue(settings)
    auth = gotrue.sign_up(email, password)
    try:
        caregivers_repo.create(auth.user_id, display_name)
    except Exception:
        gotrue.admin_delete_user(auth.user_id)  # don't leave an orphan auth user
        raise
    session_id = _persist_new_session(auth, settings, device_label=None, ua=ua, ip=ip)
    db = user_client(auth.access_token, settings)
    return session_id, caregivers_repo.onboarding_state(db, auth.user_id)


def sign_in(
    *,
    email: str,
    password: str,
    settings: Settings,
    ua: str | None = None,
    ip: str | None = None,
) -> str:
    auth = GoTrue(settings).sign_in(email, password)
    return _persist_new_session(auth, settings, device_label=None, ua=ua, ip=ip)


def request_password_reset(*, email: str, settings: Settings) -> None:
    """Ask GoTrue to email a recovery code. Deliberately swallows every
    upstream failure (unknown address, rate limit, transient error) — the
    caller must answer identically whether or not the address exists, so
    there is nothing useful to propagate."""
    with contextlib.suppress(AuthError):
        GoTrue(settings).send_recovery_otp(email)


def reset_password(
    *,
    email: str,
    code: str,
    new_password: str,
    settings: Settings,
    ua: str | None = None,
    ip: str | None = None,
) -> tuple[str, str]:
    """Trade the emailed code for a session, set the new password, then kill
    every device that was signed in before — a password reset is an
    account-takeover recovery action, so any session an attacker holds must
    die with it. Returns (device_session_id, caregiver_id).

    Deliberately does NOT touch the caregiver PIN, its failure counter, or
    its lockout — the PIN is a child-safety lock on the shared tablet, not an
    authentication factor, and clearing it here would let whoever is holding
    the device pick a new one (CLAUDE.md constraint 7).
    """
    gotrue = GoTrue(settings)
    auth = gotrue.verify_recovery_otp(email, code)
    gotrue.update_password(auth.access_token, new_password)
    # Revoke BEFORE inserting the new row, so the resetting device is created
    # after the sweep and survives without needing an `except_session`.
    sessions_repo.revoke_all_for_caregiver(auth.user_id)
    session_id = _persist_new_session(auth, settings, device_label=None, ua=ua, ip=ip)
    return session_id, auth.user_id


# --- resolution ------------------------------------------------------------


def resolve(session_id: str, settings: Settings) -> ResolvedSession:
    row = sessions_repo.get(session_id)
    if row is None or row.get("revoked_at") is not None:
        raise SessionError("session missing or revoked")

    access_token = crypto.decrypt(row["access_token_enc"], settings)
    expires_at = _parse_ts(row.get("access_token_expires_at"))

    if expires_at is None or expires_at - _REFRESH_SKEW <= datetime.now(UTC):
        access_token = _refresh(session_id, row, settings)

    return ResolvedSession(
        session_id=session_id,
        caregiver_id=row["caregiver_id"],
        access_token=access_token,
        elevated_until=_parse_ts(row.get("elevated_until")),
        _db=user_client(access_token, settings),
    )


def _refresh(session_id: str, row: dict, settings: Settings) -> str:
    refresh_token = crypto.decrypt(row["refresh_token_enc"], settings)
    try:
        auth = GoTrue(settings).refresh(refresh_token)
    except AuthError as e:
        sessions_repo.revoke(session_id)
        raise SessionError(f"refresh failed: {e.code}") from e
    sessions_repo.update_tokens(
        session_id,
        access_token_enc=crypto.encrypt(auth.access_token, settings),
        access_token_expires_at=datetime.now(UTC) + timedelta(seconds=auth.expires_in),
        refresh_token_enc=crypto.encrypt(auth.refresh_token, settings),
    )
    return auth.access_token


# --- teardown -------------------------------------------------------------


def sign_out(resolved: ResolvedSession, settings: Settings) -> None:
    GoTrue(settings).sign_out(resolved.access_token)
    sessions_repo.revoke(resolved.session_id)


def record_terms_consent(
    caregiver_id: str, settings: Settings, *, ip: str | None, ua: str | None
) -> None:
    caregivers_repo.record_terms(caregiver_id, settings.terms_version)
    consent_repo.record(
        caregiver_id=caregiver_id,
        kind="terms",
        terms_version=settings.terms_version,
        ip=ip,
        user_agent=ua,
    )


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
