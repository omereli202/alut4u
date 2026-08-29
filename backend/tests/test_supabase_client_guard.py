from __future__ import annotations

import pytest

from app.services.supabase_client import ALLOWED_SERVICE_OPERATIONS, service_client


def test_service_client_rejects_unapproved_operation(settings):
    with pytest.raises(ValueError, match="unapproved operation"):
        service_client("exfiltrate_everything", settings)


def test_allowed_operations_are_explicit_and_frozen():
    assert isinstance(ALLOWED_SERVICE_OPERATIONS, frozenset)
    assert "create_auth_user" in ALLOWED_SERVICE_OPERATIONS
