"""consent_records — append-only. Written with the service role so ``ip`` and
``user_agent`` are the values the backend observed, not client-supplied.
"""

from __future__ import annotations

from app.repositories._base import rows
from app.services.supabase_client import service_client

_TABLE = "consent_records"


def record(
    *,
    caregiver_id: str,
    kind: str,
    terms_version: str,
    child_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    resp = (
        service_client("write_consent_record")
        .table(_TABLE)
        .insert(
            {
                "caregiver_id": caregiver_id,
                "child_id": child_id,
                "kind": kind,
                "terms_version": terms_version,
                "ip": ip,
                "user_agent": user_agent,
            }
        )
        .execute()
    )
    return rows(resp)[0]
