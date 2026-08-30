"""Inactivity-based data retention.

An account whose most recent device activity (or, failing that, its creation)
is older than ``retention_warn_days`` gets a warning audit entry; older than
``retention_purge_days`` it is deleted — the GoTrue user and the full
``caregivers`` cascade — so children's data is not kept indefinitely.

Run via ``scripts/retention_purge.py`` (dry-run by default) on a schedule.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.auth.gotrue import GoTrue
from app.config import current_settings
from app.repositories import account as account_repo
from app.repositories import audit as audit_repo
from app.services.supabase_client import service_client

_log = logging.getLogger("app.retention")


@dataclass
class Sweep:
    warned: list[str] = field(default_factory=list)
    purged: list[str] = field(default_factory=list)
    dry_run: bool = True


def _last_activity(db, caregiver: dict) -> datetime:
    rows = (
        db.table("device_sessions")
        .select("last_seen_at")
        .eq("caregiver_id", caregiver["id"])
        .order("last_seen_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    ts = rows[0]["last_seen_at"] if rows else caregiver["created_at"]
    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def run(*, dry_run: bool = True) -> Sweep:
    s = current_settings()
    now = datetime.now(UTC)
    warn_before = now - timedelta(days=s.retention_warn_days)
    purge_before = now - timedelta(days=s.retention_purge_days)

    db = service_client("run_retention_purge")
    caregivers = db.table("caregivers").select("id, created_at").execute().data or []

    sweep = Sweep(dry_run=dry_run)
    gotrue = GoTrue(s)

    for cg in caregivers:
        seen = _last_activity(db, cg)
        if seen < purge_before:
            sweep.purged.append(cg["id"])
            _log.warning("retention: purge %s (idle since %s)", cg["id"], seen.date())
            if not dry_run:
                audit_repo.log(caregiver_id=cg["id"], action="retention.purge")
                gotrue.admin_delete_user(cg["id"])
                account_repo.delete_everything(cg["id"])
        elif seen < warn_before:
            sweep.warned.append(cg["id"])
            _log.info("retention: warn %s (idle since %s)", cg["id"], seen.date())
            if not dry_run:
                audit_repo.log(caregiver_id=cg["id"], action="retention.warn")

    return sweep
