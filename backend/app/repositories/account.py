"""Whole-account reads/writes for the GDPR data-subject endpoints.

Uses the service role: export must see everything the caregiver owns in one
pass, and deletion cascades from ``auth.users`` through every FK.
"""

from __future__ import annotations

from typing import Any

from app.repositories._base import one_or_none, rows
from app.services.supabase_client import service_client


def export_bundle(caregiver_id: str) -> dict[str, Any]:
    db = service_client("account_export")

    _caregiver_cols = (
        "id, display_name, pin_set_at, terms_accepted_at, "
        "terms_version, voice_consent_at, created_at"
    )
    caregiver = one_or_none(
        db.table("caregivers").select(_caregiver_cols).eq("id", caregiver_id).execute()
    )
    children = rows(db.table("children").select("*").eq("caregiver_id", caregiver_id).execute())
    child_ids = [c["id"] for c in children]

    modules = (
        rows(db.table("module_settings").select("*").in_("child_id", child_ids).execute())
        if child_ids
        else []
    )
    consents = rows(
        db.table("consent_records").select("*").eq("caregiver_id", caregiver_id).execute()
    )
    devices = rows(
        db.table("device_sessions")
        .select("id, device_label, user_agent, ip, created_at, last_seen_at, revoked_at")
        .eq("caregiver_id", caregiver_id)
        .execute()
    )
    usage = rows(db.table("usage_counters").select("*").eq("caregiver_id", caregiver_id).execute())

    return {
        "caregiver": caregiver,
        "children": children,
        "module_settings": modules,
        "consent_records": consents,
        "devices": devices,
        "usage_counters": usage,
    }


def delete_everything(caregiver_id: str) -> None:
    """Delete the caregivers row; FK ON DELETE CASCADE removes children,
    module_settings, consent_records, device_sessions, media_assets and
    usage_counters. audit_log rows survive with caregiver_id nulled."""
    service_client("delete_account_cascade").table("caregivers").delete().eq(
        "id", caregiver_id
    ).execute()
