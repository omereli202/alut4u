"""Request IDs, structured logging, optional Sentry, security headers."""

from __future__ import annotations

import json
import logging
import time
import uuid

from flask import Flask, g, request

from app.config import Settings

_REQUEST_ID_HEADER = "X-Request-Id"


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status", "ms", "caregiver_id"):
            if (val := getattr(record, key, None)) is not None:
                payload[key] = val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: Settings) -> None:
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    handler = logging.StreamHandler()
    handler.setFormatter(
        _JsonFormatter()
        if settings.json_logs
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root.handlers = [handler]


def init_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
    except ImportError:  # pragma: no cover
        logging.getLogger("app").warning("SENTRY_DSN set but sentry-sdk not installed")
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.0,
        send_default_pii=False,
    )


def register(app: Flask, settings: Settings) -> None:
    access_log = logging.getLogger("app.access")

    @app.before_request
    def _start():
        g.request_id = request.headers.get(_REQUEST_ID_HEADER) or uuid.uuid4().hex[:16]
        g._t0 = time.perf_counter()

    @app.after_request
    def _finish(resp):
        rid = getattr(g, "request_id", "-")
        resp.headers[_REQUEST_ID_HEADER] = rid
        # Security headers for every response (Caddy adds its own for static).
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if not request.path.startswith("/api/"):
            # Frontend responses (local-dev single-process; Caddy sets its own in prod).
            resp.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
                "script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            )
        if settings.is_production:
            resp.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        if request.path.startswith("/api/") and request.path != "/api/health":
            access_log.info(
                "request",
                extra={
                    "request_id": rid,
                    "method": request.method,
                    "path": request.path,
                    "status": resp.status_code,
                    "ms": round((time.perf_counter() - getattr(g, "_t0", 0)) * 1000, 1),
                    "caregiver_id": getattr(g, "caregiver_id", None),
                },
            )
        return resp
