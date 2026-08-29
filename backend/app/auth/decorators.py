"""Route guards.

``@require_session`` resolves the cookie to a :class:`ResolvedSession` on
``flask.g`` (``g.session``, ``g.db``, ``g.caregiver_id``) or 401s and clears the
cookie. ``@require_caregiver_mode`` additionally requires a live PIN elevation.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import current_app, g, jsonify, session

from app.auth import sessions

COOKIE_KEY = "sid"


def _clear_cookie_response(message: str, status: int = 401):
    session.pop(COOKIE_KEY, None)
    return jsonify(error=message), status


def require_session(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any):
        sid = session.get(COOKIE_KEY)
        if not sid:
            return jsonify(error="not_authenticated"), 401
        try:
            resolved = sessions.resolve(sid, current_app.config["SETTINGS"])
        except sessions.SessionError:
            return _clear_cookie_response("session_expired")
        g.session = resolved
        g.db = resolved.db
        g.caregiver_id = resolved.caregiver_id
        return fn(*args, **kwargs)

    return wrapper


def require_caregiver_mode(fn: Callable) -> Callable:
    @wraps(fn)
    @require_session
    def wrapper(*args: Any, **kwargs: Any):
        if not g.session.is_elevated():
            return jsonify(error="caregiver_mode_required"), 403
        return fn(*args, **kwargs)

    return wrapper
