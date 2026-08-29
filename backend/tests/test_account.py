from __future__ import annotations

from tests.conftest import requires_supabase

pytestmark = requires_supabase


def test_export_bundle_shape(client, caregiver_mode):
    client.post("/api/children", json={"name": "child", "consent_basis": "parent"})
    r = client.get("/api/account/export")
    assert r.status_code == 200
    assert r.headers["Content-Disposition"].startswith("attachment")
    bundle = r.get_json()
    assert set(bundle) >= {
        "caregiver",
        "children",
        "module_settings",
        "consent_records",
        "devices",
        "usage_counters",
    }
    assert bundle["caregiver"]["id"] == caregiver_mode["caregiver_id"]
    assert len(bundle["children"]) == 1
    assert len(bundle["module_settings"]) == 1
    # terms consent recorded at signup
    kinds = {c["kind"] for c in bundle["consent_records"]}
    assert "terms" in kinds


def test_export_requires_caregiver_mode(client, signed_up):
    assert client.get("/api/account/export").status_code == 403


def test_delete_requires_confirmation(client, caregiver_mode):
    assert client.delete("/api/account", json={"confirm": "nope"}).status_code == 422


def test_delete_cascades_and_invalidates_session(client, caregiver_mode):
    client.post("/api/children", json={"name": "child", "consent_basis": "parent"})
    assert client.delete("/api/account", json={"confirm": "DELETE"}).status_code == 204
    assert client.get("/api/auth/session").status_code == 401
    # Cannot log back in.
    r = client.post(
        "/api/auth/login",
        json={"email": caregiver_mode["email"], "password": caregiver_mode["password"]},
    )
    assert r.status_code == 401
