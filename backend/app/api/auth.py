"""Authentication & session endpoints.

Sign-up / sign-in happen server-side against GoTrue; the client only ever gets a
signed HttpOnly cookie holding a device-session id.
"""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, session

from app.api._helpers import ApiError, client_ip, parse_body, user_agent
from app.auth import pin as pin_svc
from app.auth import sessions as session_svc
from app.auth.decorators import COOKIE_KEY, require_caregiver_mode, require_session
from app.auth.gotrue import AuthError
from app.extensions import limiter
from app.repositories import audit as audit_repo
from app.repositories import caregivers as caregivers_repo
from app.repositories import consent as consent_repo
from app.repositories import device_sessions as sessions_repo
from app.schemas.auth import (
    AcceptTermsRequest,
    LoginRequest,
    PinRequest,
    SessionInfo,
    SignupRequest,
    VoiceConsentRequest,
)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _settings():
    return current_app.config["SETTINGS"]


def _bind_session(resolved) -> None:
    g.session = resolved
    g.db = resolved.db
    g.caregiver_id = resolved.caregiver_id


def _session_info() -> dict:
    resolved = g.session
    state = caregivers_repo.onboarding_state(resolved.db, resolved.caregiver_id)
    elevated = resolved.is_elevated()
    return SessionInfo(
        caregiver_id=resolved.caregiver_id,
        mode="caregiver" if elevated else "user",
        elevated_until=resolved.elevated_until.isoformat() if elevated else None,
        onboarding=state,
    ).model_dump()


@bp.post("/signup")
@limiter.limit("5 per hour; 20 per day")
def signup():
    data = parse_body(SignupRequest)
    try:
        session_id, _ = session_svc.sign_up(
            email=data.email,
            password=data.password,
            display_name=data.display_name,
            settings=_settings(),
            ua=user_agent(),
            ip=client_ip(),
        )
    except AuthError as e:
        if e.code in {"user_already_exists", "email_exists"}:
            raise ApiError(409, "email_in_use") from e
        raise ApiError(e.status if e.status < 500 else 502, e.code, e.message) from e

    session.clear()
    session[COOKIE_KEY] = session_id
    session.permanent = True

    resolved = session_svc.resolve(session_id, _settings())
    _bind_session(resolved)
    session_svc.record_terms_consent(
        resolved.caregiver_id, _settings(), ip=client_ip(), ua=user_agent()
    )
    audit_repo.log(caregiver_id=resolved.caregiver_id, action="account.signup")
    return jsonify(_session_info()), 201


@bp.post("/login")
@limiter.limit("10 per minute; 60 per hour")
def login():
    data = parse_body(LoginRequest)
    try:
        session_id = session_svc.sign_in(
            email=data.email,
            password=data.password,
            settings=_settings(),
            ua=user_agent(),
            ip=client_ip(),
        )
    except AuthError as e:
        if e.status in {400, 401, 403}:
            raise ApiError(401, "invalid_credentials") from e
        raise ApiError(502, e.code, e.message) from e

    session.clear()
    session[COOKIE_KEY] = session_id
    session.permanent = True
    _bind_session(session_svc.resolve(session_id, _settings()))
    audit_repo.log(caregiver_id=g.caregiver_id, action="account.login")
    return jsonify(_session_info())


@bp.post("/logout")
@require_session
def logout():
    session_svc.sign_out(g.session, _settings())
    session.pop(COOKIE_KEY, None)
    return "", 204


@bp.get("/session")
@require_session
def whoami():
    sessions_repo.touch(g.session.session_id)
    return jsonify(_session_info())


@bp.put("/pin")
@require_session
def set_pin():
    data = parse_body(PinRequest)
    state = caregivers_repo.onboarding_state(g.session.db, g.caregiver_id)
    # Changing an existing PIN requires being in Caregiver Mode already.
    if not state["needs_pin"] and not g.session.is_elevated():
        raise ApiError(403, "caregiver_mode_required")
    try:
        pin_svc.set_pin(g.caregiver_id, data.pin, _settings())
    except pin_svc.PinError as e:
        raise ApiError(422, "weak_pin", str(e)) from e
    return "", 204


@bp.post("/pin")
@require_session
@limiter.limit("15 per minute")
def verify_pin():
    data = parse_body(PinRequest)
    try:
        result = pin_svc.verify_pin(g.caregiver_id, data.pin, g.session.session_id, _settings())
    except pin_svc.PinLockedError as e:
        raise ApiError(429, "pin_locked", f"retry after {e.retry_after_seconds}s") from e
    except pin_svc.PinError as e:
        raise ApiError(401, "pin_incorrect", str(e)) from e
    return jsonify(mode="caregiver", elevated_until=result.elevated_until.isoformat())


@bp.delete("/pin/elevation")
@require_session
def exit_caregiver_mode():
    pin_svc.drop_elevation(g.session.session_id)
    return "", 204


@bp.post("/terms")
@require_session
def accept_terms():
    data = parse_body(AcceptTermsRequest)
    if not data.accept:
        raise ApiError(422, "must_accept")
    session_svc.record_terms_consent(g.caregiver_id, _settings(), ip=client_ip(), ua=user_agent())
    return "", 204


@bp.post("/voice-consent")
@require_caregiver_mode
def voice_consent():
    data = parse_body(VoiceConsentRequest)
    if not data.accept:
        raise ApiError(422, "must_accept")
    caregivers_repo.set_voice_consent(g.caregiver_id)
    consent_repo.record(
        caregiver_id=g.caregiver_id,
        kind="voice_recording",
        terms_version=_settings().terms_version,
        ip=client_ip(),
        user_agent=user_agent(),
    )
    audit_repo.log(caregiver_id=g.caregiver_id, action="consent.voice_recording")
    return "", 204


@bp.get("/devices")
@require_caregiver_mode
def list_devices():
    return jsonify(devices=sessions_repo.list_for_caregiver(g.session.db, g.caregiver_id))


@bp.delete("/devices/<device_id>")
@require_caregiver_mode
def revoke_device(device_id: str):
    owned = {d["id"] for d in sessions_repo.list_for_caregiver(g.session.db, g.caregiver_id)}
    if device_id not in owned:
        raise ApiError(404, "not_found")
    sessions_repo.revoke(device_id)
    audit_repo.log(
        caregiver_id=g.caregiver_id,
        action="device.revoke",
        target_type="device_session",
        target_id=device_id,
    )
    return "", 204
