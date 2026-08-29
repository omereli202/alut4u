"""Caregiver-Mode PIN: set, verify (with escalating lockout), and the
time-boxed elevation that verification grants on the current device session.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.auth import crypto
from app.config import Settings
from app.repositories import audit as audit_repo
from app.repositories import caregivers as caregivers_repo
from app.repositories import device_sessions as sessions_repo

_PIN_RE = re.compile(r"^\d{4}$")


class PinError(Exception):
    pass


class PinLockedError(PinError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"locked for {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True, slots=True)
class PinVerifyResult:
    elevated_until: datetime


def validate_pin_format(pin: str) -> None:
    if not _PIN_RE.match(pin or ""):
        raise PinError("PIN must be exactly 4 digits")
    if len(set(pin)) == 1 or pin in {"1234", "0000", "1111"}:
        raise PinError("PIN is too easy to guess")


def set_pin(caregiver_id: str, pin: str, settings: Settings) -> None:
    validate_pin_format(pin)
    caregivers_repo.set_pin_hash(caregiver_id, crypto.hash_pin(pin, settings))
    audit_repo.log(caregiver_id=caregiver_id, action="pin.set")


def verify_pin(caregiver_id: str, pin: str, session_id: str, settings: Settings) -> PinVerifyResult:
    state = caregivers_repo.pin_state(caregiver_id)
    if not state or not state.get("pin_hash"):
        raise PinError("no PIN is set")

    locked_until = _parse_ts(state.get("pin_locked_until"))
    now = datetime.now(UTC)
    if locked_until and locked_until > now:
        raise PinLockedError(int((locked_until - now).total_seconds()) + 1)

    if not crypto.verify_pin(state["pin_hash"], pin, settings):
        _register_failure(caregiver_id, state.get("pin_failed_attempts", 0), settings)
        raise PinError("incorrect PIN")

    caregivers_repo.reset_pin_failures(caregiver_id)
    if crypto.pin_needs_rehash(state["pin_hash"]):
        caregivers_repo.set_pin_hash(caregiver_id, crypto.hash_pin(pin, settings))

    elevated_until = now + timedelta(minutes=settings.caregiver_elevation_minutes)
    sessions_repo.set_elevation(session_id, elevated_until)
    audit_repo.log(caregiver_id=caregiver_id, action="pin.verify_ok")
    return PinVerifyResult(elevated_until=elevated_until)


def drop_elevation(session_id: str) -> None:
    sessions_repo.clear_elevation(session_id)


def _register_failure(caregiver_id: str, prev_attempts: int, settings: Settings) -> None:
    attempts = prev_attempts + 1
    locked_until: datetime | None = None
    if attempts >= settings.pin_lockout_after:
        steps = settings.pin_lockout_steps_seconds
        idx = min(attempts - settings.pin_lockout_after, len(steps) - 1)
        locked_until = datetime.now(UTC) + timedelta(seconds=steps[idx])
    caregivers_repo.bump_pin_failure(caregiver_id, attempts, locked_until)
    audit_repo.log(
        caregiver_id=caregiver_id,
        action="pin.verify_fail",
        detail={"attempts": attempts, "locked": locked_until is not None},
    )


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
