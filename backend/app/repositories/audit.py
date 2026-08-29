"""audit_log — sensitive actions. Service-role only (no RLS policy exists)."""

from __future__ import annotations

from app.services.supabase_client import service_client


def log(
    *,
    caregiver_id: str | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
) -> None:
    service_client("write_audit_log").table("audit_log").insert(
        {
            "caregiver_id": caregiver_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "detail": detail or {},
        }
    ).execute()
