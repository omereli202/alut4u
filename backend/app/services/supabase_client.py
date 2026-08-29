"""Supabase client construction.

Two kinds of client, and the distinction is a security boundary:

* :func:`user_client` — authenticated as a specific caregiver's JWT. Every
  request that touches caregiver/child data uses one of these, so Postgres RLS
  is what actually enforces tenancy. This is the default.

* :func:`service_client` — uses the service-role key, which **bypasses RLS**.
  Allowed only for the operations in :data:`ALLOWED_SERVICE_OPERATIONS`. Callers
  pass the operation name so misuse is greppable and reviewable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import Settings, current_settings

if TYPE_CHECKING:  # avoid importing the heavy SDK at module load
    from supabase import Client

# Every legitimate reason to bypass RLS. Adding to this list is a security
# review, not a casual change.
ALLOWED_SERVICE_OPERATIONS: frozenset[str] = frozenset(
    {
        "create_auth_user",  # sign-up: insert the caregivers row
        "manage_device_session",  # read/write device_sessions before a user JWT exists
        "pin_state",  # read/update caregivers PIN lockout + hash
        "write_consent_record",  # server-attested consent rows (trusted ip / ua)
        "write_audit_log",  # sensitive-action log (no RLS policy on the table)
        "write_usage_counter",  # per-caregiver monthly usage tallies
        "delete_account_cascade",  # GDPR erasure across tables + storage
        "account_export",  # read-all for the data-subject export bundle
        "write_tts_cache",  # shared, non-tenant TTS audio cache
        "read_symbol_library",  # global read-only symbol table
        "run_retention_purge",  # scheduled inactivity cleanup
        "seed_board_template",  # apply a starter board on child creation
    }
)


def user_client(access_token: str, settings: Settings | None = None) -> Client:
    """Client scoped to one caregiver. RLS applies."""
    from supabase import ClientOptions, create_client

    s = settings or current_settings()
    client = create_client(
        s.supabase_url,
        s.supabase_anon_key,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )
    client.postgrest.auth(access_token)
    return client


def service_client(operation: str, settings: Settings | None = None) -> Client:
    """Client that bypasses RLS. ``operation`` must be pre-approved."""
    if operation not in ALLOWED_SERVICE_OPERATIONS:
        raise ValueError(
            f"service_client called with unapproved operation {operation!r}; "
            f"add it to ALLOWED_SERVICE_OPERATIONS only after security review"
        )
    from supabase import ClientOptions, create_client

    s = settings or current_settings()
    return create_client(
        s.supabase_url,
        s.supabase_service_role_key,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )
