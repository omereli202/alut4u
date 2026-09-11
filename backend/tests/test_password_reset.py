"""Unit tests for the password-reset GoTrue calls and the app-level error
mapping. Pure httpx mocking via respx — no local Supabase stack needed, so
this file is NOT marked requires_supabase and always runs in CI.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from app.api.auth import _reset_error
from app.auth.gotrue import AuthError, GoTrue
from tests.conftest import LOCAL_SUPABASE_URL

AUTH = f"{LOCAL_SUPABASE_URL}/auth/v1"


@pytest.fixture
def gotrue(settings):
    return GoTrue(settings)


def _session_payload(uid="11111111-1111-1111-1111-111111111111"):
    return {
        "access_token": "recovery-token",
        "refresh_token": "rt",
        "expires_in": 3600,
        "user": {"id": uid, "email": "a@example.com"},
    }


# --- send_recovery_otp -------------------------------------------------------


@respx.mock
def test_recover_posts_only_the_email(gotrue):
    route = respx.post(f"{AUTH}/recover").mock(return_value=httpx.Response(200, json={}))
    gotrue.send_recovery_otp("a@example.com")
    assert route.called
    req = route.calls[0].request
    assert req.headers["apikey"]
    import json as _json

    assert _json.loads(req.content) == {"email": "a@example.com"}


@respx.mock
def test_recover_on_unknown_address_does_not_raise(gotrue):
    respx.post(f"{AUTH}/recover").mock(return_value=httpx.Response(200, json={}))
    gotrue.send_recovery_otp("nobody@example.com")  # must not raise


# --- verify_recovery_otp -----------------------------------------------------


@respx.mock
def test_verify_sends_type_recovery_and_returns_a_session(gotrue):
    route = respx.post(f"{AUTH}/verify").mock(
        return_value=httpx.Response(200, json=_session_payload())
    )
    session = gotrue.verify_recovery_otp("a@example.com", "123456")
    import json as _json

    assert _json.loads(route.calls[0].request.content) == {
        "type": "recovery",
        "email": "a@example.com",
        "token": "123456",
    }
    assert session.user_id == "11111111-1111-1111-1111-111111111111"
    assert session.access_token == "recovery-token"
    assert session.expires_in == 3600


@respx.mock
def test_expired_code_raises_auth_error(gotrue):
    respx.post(f"{AUTH}/verify").mock(
        return_value=httpx.Response(
            403,
            json={"error_code": "otp_expired", "msg": "Email link is invalid or has expired"},
        )
    )
    with pytest.raises(AuthError) as exc:
        gotrue.verify_recovery_otp("a@example.com", "000000")
    assert exc.value.status == 403
    assert exc.value.code == "otp_expired"


@respx.mock
def test_legacy_error_body_without_error_code(gotrue):
    """Older GoTrue builds omit error_code entirely."""
    respx.post(f"{AUTH}/verify").mock(
        return_value=httpx.Response(
            401,
            json={
                "error": "invalid_request",
                "error_description": "Token has expired or is invalid",
            },
        )
    )
    with pytest.raises(AuthError) as exc:
        gotrue.verify_recovery_otp("a@example.com", "123456")
    assert exc.value.status == 401
    assert exc.value.code == "invalid_request"


@respx.mock
def test_unknown_user_raises_user_not_found(gotrue):
    respx.post(f"{AUTH}/verify").mock(
        return_value=httpx.Response(404, json={"error_code": "user_not_found"})
    )
    with pytest.raises(AuthError) as exc:
        gotrue.verify_recovery_otp("nobody@example.com", "123456")
    assert exc.value.code == "user_not_found"


@respx.mock
def test_upstream_unreachable_is_502(gotrue):
    respx.post(f"{AUTH}/verify").mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(AuthError) as exc:
        gotrue.verify_recovery_otp("a@example.com", "123456")
    assert exc.value.status == 502
    assert exc.value.code == "upstream_unreachable"


# --- update_password ---------------------------------------------------------


@respx.mock
def test_update_password_puts_user_with_the_recovery_bearer(gotrue):
    route = respx.put(f"{AUTH}/user").mock(return_value=httpx.Response(200, json={"id": "u1"}))
    gotrue.update_password("recovery-token", "new-password-123")
    req = route.calls[0].request
    assert req.headers["Authorization"] == "Bearer recovery-token"
    import json as _json

    assert _json.loads(req.content) == {"password": "new-password-123"}


@respx.mock
def test_weak_password_raises_422(gotrue):
    respx.put(f"{AUTH}/user").mock(
        return_value=httpx.Response(422, json={"error_code": "weak_password"})
    )
    with pytest.raises(AuthError) as exc:
        gotrue.update_password("recovery-token", "short")
    assert exc.value.status == 422
    assert exc.value.code == "weak_password"


# --- app.api.auth._reset_error mapping ---------------------------------------
# The whole point of this endpoint is that an unknown address and a
# known-but-wrong code produce the SAME app-level error, so neither leaks
# account existence.


@pytest.mark.parametrize(
    "status,code",
    [
        (403, "otp_expired"),
        (404, "user_not_found"),
        (400, "validation_failed"),
    ],
)
def test_reset_error_collapses_known_gotrue_failures_to_invalid_code(status, code):
    err = _reset_error(AuthError(status, code, "boom"))
    assert err.status == 400
    assert err.code == "invalid_code"


@pytest.mark.parametrize("code", ["weak_password", "same_password"])
def test_reset_error_maps_weak_password_codes_to_422(code):
    err = _reset_error(AuthError(422, code, "boom"))
    assert err.status == 422
    assert err.code == code


def test_reset_error_maps_429_to_rate_limited():
    err = _reset_error(AuthError(429, "over_request_rate_limit", "boom"))
    assert err.status == 429
    assert err.code == "rate_limited"


def test_reset_error_maps_unknown_5xx_to_502():
    err = _reset_error(AuthError(500, "some_upstream_error", "boom"))
    assert err.status == 502
    assert err.code == "some_upstream_error"
