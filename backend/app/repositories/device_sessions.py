"""device_sessions table access.

One row per signed-in device. The backend needs these rows before it has a user
JWT (to resolve the session cookie), so all access here is service-role. Token
columns hold Fernet-encrypted values.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.repositories._base import one_or_none, rows
from app.services.supabase_client import service_client

_TABLE = "device_sessions"


def _svc():
    return service_client("manage_device_session")


def create(
    *,
    caregiver_id: str,
    refresh_token_enc: str,
    access_token_enc: str,
    access_token_expires_at: datetime,
    device_label: str | None,
    user_agent: str | None,
    ip: str | None,
) -> dict:
    resp = (
        _svc()
        .table(_TABLE)
        .insert(
            {
                "caregiver_id": caregiver_id,
                "refresh_token_enc": refresh_token_enc,
                "access_token_enc": access_token_enc,
                "access_token_expires_at": access_token_expires_at.isoformat(),
                "device_label": device_label,
                "user_agent": user_agent,
                "ip": ip,
            }
        )
        .execute()
    )
    return one_or_none(resp)


def get(session_id: str) -> dict | None:
    return one_or_none(_svc().table(_TABLE).select("*").eq("id", session_id).execute())


def update_tokens(
    session_id: str,
    *,
    access_token_enc: str,
    access_token_expires_at: datetime,
    refresh_token_enc: str,
) -> None:
    _svc().table(_TABLE).update(
        {
            "access_token_enc": access_token_enc,
            "access_token_expires_at": access_token_expires_at.isoformat(),
            "refresh_token_enc": refresh_token_enc,
            "last_seen_at": _now(),
        }
    ).eq("id", session_id).execute()


def touch(session_id: str) -> None:
    _svc().table(_TABLE).update({"last_seen_at": _now()}).eq("id", session_id).execute()


def set_elevation(session_id: str, until: datetime) -> None:
    _svc().table(_TABLE).update({"elevated_until": until.isoformat()}).eq(
        "id", session_id
    ).execute()


def clear_elevation(session_id: str) -> None:
    _svc().table(_TABLE).update({"elevated_until": None}).eq("id", session_id).execute()


def revoke(session_id: str) -> None:
    _svc().table(_TABLE).update({"revoked_at": _now()}).eq("id", session_id).execute()


def revoke_all_for_caregiver(caregiver_id: str, *, except_session: str | None = None) -> None:
    q = _svc().table(_TABLE).update({"revoked_at": _now()}).eq("caregiver_id", caregiver_id)
    q = q.is_("revoked_at", "null")
    if except_session:
        q = q.neq("id", except_session)
    q.execute()


def list_for_caregiver(db: Any, caregiver_id: str) -> list[dict]:
    """Caregiver-facing device list (RLS: owner select). No token columns."""
    return rows(
        db.table(_TABLE)
        .select("id, device_label, user_agent, created_at, last_seen_at, revoked_at")
        .eq("caregiver_id", caregiver_id)
        .order("last_seen_at", desc=True)
        .execute()
    )


def _now() -> str:
    return datetime.now().astimezone().isoformat()
