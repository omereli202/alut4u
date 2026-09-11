"""Thin server-side client for Supabase Auth (GoTrue).

The browser never talks to GoTrue directly — Flask does, then issues its own
signed session cookie. Only the few operations we actually use are wrapped.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass

import httpx

from app.config import Settings


@dataclass(frozen=True, slots=True)
class AuthSession:
    user_id: str
    email: str
    access_token: str
    refresh_token: str
    expires_in: int


class AuthError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message


class GoTrue:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.supabase_url.rstrip("/") + "/auth/v1"
        self._anon = settings.supabase_anon_key
        self._service = settings.supabase_service_role_key

    def _send(self, method: str, path: str, *, json: dict, bearer: str | None = None) -> dict:
        headers = {"apikey": self._anon, "Authorization": f"Bearer {bearer or self._anon}"}
        try:
            r = httpx.request(method, self._base + path, json=json, headers=headers, timeout=15.0)
        except httpx.HTTPError as e:
            raise AuthError(502, "upstream_unreachable", str(e)) from e
        return self._handle(r)

    def _post(self, path: str, *, json: dict, bearer: str | None = None) -> dict:
        return self._send("POST", path, json=json, bearer=bearer)

    def _put(self, path: str, *, json: dict, bearer: str | None = None) -> dict:
        return self._send("PUT", path, json=json, bearer=bearer)

    @staticmethod
    def _handle(r: httpx.Response) -> dict:
        if r.status_code >= 400:
            body = {}
            with contextlib.suppress(ValueError):
                body = r.json()
            code = body.get("error_code") or body.get("error") or "auth_error"
            msg = body.get("msg") or body.get("error_description") or body.get("message") or r.text
            raise AuthError(r.status_code, str(code), str(msg)[:300])
        return r.json() if r.content else {}

    @staticmethod
    def _session_from(payload: dict) -> AuthSession:
        user = payload.get("user") or {}
        return AuthSession(
            user_id=user.get("id") or payload["user"]["id"],
            email=user.get("email", ""),
            access_token=payload["access_token"],
            refresh_token=payload["refresh_token"],
            expires_in=int(payload.get("expires_in", 3600)),
        )

    def sign_up(self, email: str, password: str) -> AuthSession:
        payload = self._post("/signup", json={"email": email, "password": password})
        if "access_token" not in payload:
            # Email-confirmation flow is on; we don't support it in Phase 1.
            raise AuthError(
                400, "email_confirmation_required", "email confirmation is not supported"
            )
        return self._session_from(payload)

    def sign_in(self, email: str, password: str) -> AuthSession:
        payload = self._post(
            "/token?grant_type=password", json={"email": email, "password": password}
        )
        return self._session_from(payload)

    def refresh(self, refresh_token: str) -> AuthSession:
        payload = self._post(
            "/token?grant_type=refresh_token", json={"refresh_token": refresh_token}
        )
        return self._session_from(payload)

    def send_recovery_otp(self, email: str) -> None:
        """POST /recover — GoTrue emails a 6-digit code (see the recovery
        template in supabase/config.toml). Answers 200 whether or not the
        address has an account; nothing here should ever be surfaced to a
        caller in a way that reveals which case happened."""
        self._post("/recover", json={"email": email})

    def verify_recovery_otp(self, email: str, token: str) -> AuthSession:
        """POST /verify — trades the emailed code for a real session. The
        code is single-use: a second call with the same token fails."""
        payload = self._post("/verify", json={"type": "recovery", "email": email, "token": token})
        return self._session_from(payload)

    def update_password(self, access_token: str, password: str) -> None:
        """PUT /user, authenticated as the recovery session — never the
        caller's own bearer, so a stolen access token alone can't do this."""
        self._put("/user", json={"password": password}, bearer=access_token)

    def sign_out(self, access_token: str) -> None:
        # Revokes the refresh token server-side. Best-effort.
        with contextlib.suppress(httpx.HTTPError):
            httpx.post(
                self._base + "/logout",
                headers={"apikey": self._anon, "Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )

    def admin_delete_user(self, user_id: str) -> None:
        try:
            r = httpx.delete(
                f"{self._base}/admin/users/{user_id}",
                headers={"apikey": self._service, "Authorization": f"Bearer {self._service}"},
                timeout=15.0,
            )
        except httpx.HTTPError as e:
            raise AuthError(502, "upstream_unreachable", str(e)) from e
        if r.status_code >= 400 and r.status_code != 404:
            self._handle(r)
