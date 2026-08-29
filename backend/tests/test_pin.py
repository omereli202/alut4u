from __future__ import annotations

import json

from tests.conftest import requires_supabase

pytestmark = requires_supabase


def test_set_then_verify_grants_caregiver_mode(client, signed_up):
    assert client.put("/api/auth/pin", json={"pin": "2580"}).status_code == 204
    r = client.post("/api/auth/pin", json={"pin": "2580"})
    assert r.status_code == 200
    assert r.get_json()["mode"] == "caregiver"
    assert client.get("/api/auth/session").get_json()["mode"] == "caregiver"


def test_weak_pin_rejected(client, signed_up):
    for weak in ("1234", "0000", "1111"):
        r = client.put("/api/auth/pin", json={"pin": weak})
        assert r.status_code == 422, weak


def test_wrong_pin_then_lockout_escalation(client, signed_up):
    assert client.put("/api/auth/pin", json={"pin": "2580"}).status_code == 204

    # 5 failures allowed, 6th is locked.
    for _ in range(5):
        assert client.post("/api/auth/pin", json={"pin": "0009"}).status_code == 401
    r = client.post("/api/auth/pin", json={"pin": "0009"})
    assert r.status_code == 429
    assert r.get_json()["error"] == "pin_locked"

    # Correct PIN is still refused while locked.
    assert client.post("/api/auth/pin", json={"pin": "2580"}).status_code == 429


def test_exit_caregiver_mode_drops_elevation(client, caregiver_mode):
    assert client.get("/api/auth/session").get_json()["mode"] == "caregiver"
    assert client.delete("/api/auth/pin/elevation").status_code == 204
    assert client.get("/api/auth/session").get_json()["mode"] == "user"


def test_changing_pin_requires_caregiver_mode(client, signed_up):
    assert client.put("/api/auth/pin", json={"pin": "2580"}).status_code == 204  # onboarding
    assert client.delete("/api/auth/pin/elevation").status_code == 204
    # Now a PIN exists and we're not elevated → cannot change it.
    assert client.put("/api/auth/pin", json={"pin": "1357"}).status_code == 403


def test_pin_hash_never_appears_in_any_response(client, caregiver_mode):
    for path in ("/api/auth/session", "/api/account/export", "/api/children"):
        r = client.get(path)
        assert "pin_hash" not in json.dumps(r.get_json() or {})
