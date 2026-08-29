"""caregivers table access.

The account row is 1:1 with ``auth.users``. Creation and all PIN-lockout state
changes run with the service role (the caregiver has no JWT yet at sign-up, and
lockout counters must not be caregiver-writable). Plain profile reads use the
caregiver's own client so RLS still applies.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.repositories._base import one_or_none
from app.services.supabase_client import service_client

_TABLE = "caregivers"


def create(caregiver_id: str, display_name: str) -> dict:
    db = service_client("create_auth_user")
    resp = db.table(_TABLE).insert({"id": caregiver_id, "display_name": display_name}).execute()
    return one_or_none(resp) or {"id": caregiver_id, "display_name": display_name}


def get(db: Any, caregiver_id: str) -> dict | None:
    """Read via the caller's client (RLS: id = auth.uid())."""
    return one_or_none(db.table(_TABLE).select("*").eq("id", caregiver_id).execute())


def onboarding_state(db: Any, caregiver_id: str) -> dict:
    row = get(db, caregiver_id) or {}
    return {
        "needs_pin": row.get("pin_set_at") is None,
        "needs_terms": row.get("terms_accepted_at") is None,
        "voice_consent": row.get("voice_consent_at") is not None,
        "display_name": row.get("display_name"),
    }


# --- service-role state changes -------------------------------------------------


def _svc():
    return service_client("pin_state")


def set_pin_hash(caregiver_id: str, pin_hash: str) -> None:
    _svc().table(_TABLE).update(
        {
            "pin_hash": pin_hash,
            "pin_set_at": _now(),
            "pin_failed_attempts": 0,
            "pin_locked_until": None,
        }
    ).eq("id", caregiver_id).execute()


def record_terms(caregiver_id: str, version: str) -> None:
    _svc().table(_TABLE).update({"terms_accepted_at": _now(), "terms_version": version}).eq(
        "id", caregiver_id
    ).execute()


def set_voice_consent(caregiver_id: str) -> None:
    _svc().table(_TABLE).update({"voice_consent_at": _now()}).eq("id", caregiver_id).execute()


def pin_state(caregiver_id: str) -> dict | None:
    return one_or_none(
        _svc()
        .table(_TABLE)
        .select("pin_hash, pin_failed_attempts, pin_locked_until")
        .eq("id", caregiver_id)
        .execute()
    )


def bump_pin_failure(caregiver_id: str, attempts: int, locked_until: datetime | None) -> None:
    _svc().table(_TABLE).update(
        {
            "pin_failed_attempts": attempts,
            "pin_locked_until": locked_until.isoformat() if locked_until else None,
        }
    ).eq("id", caregiver_id).execute()


def reset_pin_failures(caregiver_id: str) -> None:
    _svc().table(_TABLE).update({"pin_failed_attempts": 0, "pin_locked_until": None}).eq(
        "id", caregiver_id
    ).execute()


def _now() -> str:
    return datetime.now().astimezone().isoformat()
