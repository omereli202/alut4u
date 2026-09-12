from __future__ import annotations

import pytest

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


# --- password reset -----------------------------------------------------
#
# The local Supabase stack really emails the code to Inbucket and the test
# can't read it, so `fake_recovery` fakes only OTP *delivery* and
# *verification*; `verify_recovery_otp` hands back a genuine password-grant
# session for the same user, so the persisted tokens are real and RLS still
# applies downstream. Everything else — PUT /user, device_sessions rows —
# stays live.


@pytest.fixture
def fake_recovery(monkeypatch, signed_up):
    from app.auth import gotrue as gotrue_mod

    sent: list[str] = []

    def _send(self, email):
        sent.append(email)

    def _verify(self, email, token):
        if token != "123456":
            raise gotrue_mod.AuthError(403, "otp_expired", "Token has expired or is invalid")
        return gotrue_mod.GoTrue.sign_in(self, email, signed_up["password"])

    monkeypatch.setattr(gotrue_mod.GoTrue, "send_recovery_otp", _send)
    monkeypatch.setattr(gotrue_mod.GoTrue, "verify_recovery_otp", _verify)
    return sent


def test_reset_request_is_202_for_a_known_and_an_unknown_address(client, fake_recovery, signed_up):
    r1 = client.post("/api/auth/password-reset", json={"email": signed_up["email"]})
    r2 = client.post("/api/auth/password-reset", json={"email": "nobody@example.com"})
    assert r1.status_code == 202
    assert r1.data == b""
    assert r2.status_code == 202
    assert r2.data == b""


def test_wrong_code_is_400_invalid_code(client, fake_recovery, signed_up):
    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"email": signed_up["email"], "code": "000000", "password": "brand-new-password-1"},
    )
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid_code"
    # No cookie swap on a failed attempt — the old session is still good.
    assert client.get("/api/auth/session").status_code == 200


def test_reset_sets_the_new_password_and_signs_in(client, fake_recovery, signed_up):
    assert client.post("/api/auth/logout").status_code == 204

    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"email": signed_up["email"], "code": "123456", "password": "brand-new-password-1"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["caregiver_id"] == signed_up["caregiver_id"]
    assert body["mode"] == "user"
    assert client.get("/api/auth/session").status_code == 200

    assert client.post("/api/auth/logout").status_code == 204
    old_login = client.post(
        "/api/auth/login", json={"email": signed_up["email"], "password": signed_up["password"]}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login",
        json={"email": signed_up["email"], "password": "brand-new-password-1"},
    )
    assert new_login.status_code == 200


def test_reset_revokes_every_other_device(app, client, fake_recovery, signed_up):
    other = app.test_client()
    r = other.post(
        "/api/auth/login",
        json={"email": signed_up["email"], "password": signed_up["password"]},
    )
    assert r.status_code == 200
    assert other.get("/api/auth/session").status_code == 200

    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"email": signed_up["email"], "code": "123456", "password": "brand-new-password-1"},
    )
    assert r.status_code == 200

    assert other.get("/api/auth/session").status_code == 401
    assert client.get("/api/auth/session").status_code == 200


def test_reset_does_not_reset_the_caregiver_pin(client, fake_recovery, caregiver_mode):
    r = client.post(
        "/api/auth/password-reset/confirm",
        json={
            "email": caregiver_mode["email"],
            "code": "123456",
            "password": "brand-new-password-1",
        },
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["mode"] == "user"
    assert body["elevated_until"] is None
    assert body["onboarding"]["needs_pin"] is False

    # The old PIN still works — it was never touched.
    assert client.post("/api/auth/pin", json={"pin": "2580"}).status_code == 200


def test_short_password_is_rejected_before_the_code_is_used(client, fake_recovery, signed_up):
    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"email": signed_up["email"], "code": "123456", "password": "short"},
    )
    assert r.status_code == 422

    # The code must still work — proves parse_body ran (and rejected) before
    # any GoTrue call burned the OTP.
    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"email": signed_up["email"], "code": "123456", "password": "brand-new-password-1"},
    )
    assert r.status_code == 200


@pytest.mark.parametrize("code", ["12345", "abcdef", "1234567"])
def test_code_must_be_six_digits(client, fake_recovery, signed_up, code):
    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"email": signed_up["email"], "code": code, "password": "brand-new-password-1"},
    )
    assert r.status_code == 422


def test_reset_works_without_a_session_cookie(app, fake_recovery, signed_up):
    fresh = app.test_client()
    r = fresh.post(
        "/api/auth/password-reset/confirm",
        json={"email": signed_up["email"], "code": "123456", "password": "brand-new-password-1"},
    )
    assert r.status_code == 200
    assert fresh.get("/api/auth/session").status_code == 200
