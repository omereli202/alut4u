from __future__ import annotations

from tests.conftest import requires_supabase

pytestmark = requires_supabase


def test_signup_sets_session_and_records_terms(client, new_email):
    r = client.post(
        "/api/auth/signup",
        json={
            "email": new_email,
            "password": "test-password-123",
            "display_name": "הורה",
            "accept_terms": True,
        },
    )
    assert r.status_code == 201
    body = r.get_json()
    assert body["mode"] == "user"
    assert body["onboarding"]["needs_pin"] is True
    assert body["onboarding"]["needs_terms"] is False  # recorded at signup


def test_signup_requires_accepting_terms(client, new_email):
    r = client.post(
        "/api/auth/signup",
        json={
            "email": new_email,
            "password": "test-password-123",
            "display_name": "x",
            "accept_terms": False,
        },
    )
    assert r.status_code == 422


def test_duplicate_email_is_409(client, new_email):
    payload = {
        "email": new_email,
        "password": "test-password-123",
        "display_name": "x",
        "accept_terms": True,
    }
    assert client.post("/api/auth/signup", json=payload).status_code == 201
    client.delete("/api/auth/pin/elevation")  # no-op; fresh client cookie kept
    r = client.post("/api/auth/signup", json=payload)
    assert r.status_code == 409
    assert r.get_json()["error"] == "email_in_use"


def test_login_after_signup(client, signed_up):
    # New client instance would be cleaner, but reusing: log out then back in.
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/session").status_code == 401

    r = client.post(
        "/api/auth/login",
        json={"email": signed_up["email"], "password": signed_up["password"]},
    )
    assert r.status_code == 200
    assert r.get_json()["caregiver_id"] == signed_up["caregiver_id"]


def test_bad_login_is_401(client):
    r = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"}
    )
    assert r.status_code == 401
    assert r.get_json()["error"] == "invalid_credentials"


def test_session_endpoint_requires_cookie(client):
    assert client.get("/api/auth/session").status_code == 401
