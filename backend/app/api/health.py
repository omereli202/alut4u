"""Health check — used by Railway's healthcheck and uptime monitoring.

Cheap by default (no external calls). ``?deep=1`` additionally checks that the
Supabase REST endpoint is reachable, for use in a readiness probe.
"""

from __future__ import annotations

import httpx
from flask import Blueprint, current_app, jsonify, request

from app.config import Settings

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    settings: Settings = current_app.config["SETTINGS"]
    body = {
        "status": "ok",
        "env": settings.app_env,
        "version": _version(),
    }

    if request.args.get("deep") == "1":
        body["checks"] = {"supabase": _check_supabase(settings)}
        if body["checks"]["supabase"] != "ok":
            body["status"] = "degraded"
            return jsonify(body), 503

    return jsonify(body), 200


def _version() -> str:
    import os

    return os.environ.get("RAILWAY_GIT_COMMIT_SHA", "dev")[:12]


def _check_supabase(settings: Settings) -> str:
    if not settings.supabase_url:
        return "unconfigured"
    try:
        r = httpx.get(
            f"{settings.supabase_url}/auth/v1/health",
            headers={"apikey": settings.supabase_anon_key},
            timeout=3.0,
        )
        return "ok" if r.status_code < 500 else f"http_{r.status_code}"
    except httpx.HTTPError as e:
        return f"error:{type(e).__name__}"
