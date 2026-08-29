from __future__ import annotations

import os
import uuid

import httpx
import pytest

from app import create_app
from app.config import Settings

# Well-known local Supabase demo values (identical on every machine). CI and
# local dev both run `supabase start` before the suite.
LOCAL_SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
LOCAL_ANON = os.environ.get(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0",
)
LOCAL_SERVICE = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU",
)
LOCAL_JWT_SECRET = os.environ.get(
    "SUPABASE_JWT_SECRET", "super-secret-jwt-token-with-at-least-32-characters-long"
)
# A valid Fernet key — tests only need round-tripping, not secrecy.
TEST_FERNET_KEY = "lYDZMo6dc2NQYI3Zg0cDRCNrfru0pOENOessLeuaaHU="


def _supabase_up() -> bool:
    try:
        r = httpx.get(
            f"{LOCAL_SUPABASE_URL}/auth/v1/health",
            headers={"apikey": LOCAL_ANON},
            timeout=2,
        )
        return r.status_code < 500
    except httpx.HTTPError:
        return False


requires_supabase = pytest.mark.skipif(
    not _supabase_up(), reason="local Supabase stack not running (`supabase start`)"
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        flask_secret_key="test-secret",
        serve_frontend=False,
        supabase_url=LOCAL_SUPABASE_URL,
        supabase_anon_key=LOCAL_ANON,
        supabase_service_role_key=LOCAL_SERVICE,
        supabase_jwt_secret=LOCAL_JWT_SECRET,
        session_token_enc_key=TEST_FERNET_KEY,
        pin_pepper="test-pepper",
    )


@pytest.fixture
def app(settings: Settings):
    from app.extensions import limiter

    application = create_app(settings)
    application.config.update(TESTING=True)
    limiter.enabled = False  # no rate limiting inside the suite
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def new_email() -> str:
    return f"test-{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
def signed_up(client, new_email):
    """A signed-up caregiver with the session cookie set on `client`.
    Returns a small dict with the email and caregiver_id."""
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": new_email,
            "password": "test-password-123",
            "display_name": "Test Caregiver",
            "accept_terms": True,
        },
    )
    assert resp.status_code == 201, resp.get_json()
    return {
        "email": new_email,
        "caregiver_id": resp.get_json()["caregiver_id"],
        "password": "test-password-123",
    }


@pytest.fixture
def caregiver_mode(client, signed_up):
    """signed_up, plus a PIN set and verified so the client is in Caregiver Mode."""
    assert client.put("/api/auth/pin", json={"pin": "2580"}).status_code == 204
    assert client.post("/api/auth/pin", json={"pin": "2580"}).status_code == 200
    return signed_up
