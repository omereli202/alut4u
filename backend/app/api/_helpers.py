"""Small shared helpers for API blueprints."""

from __future__ import annotations

from flask import request
from pydantic import BaseModel, ValidationError
from werkzeug.exceptions import BadRequest


class ApiError(Exception):
    def __init__(self, status: int, code: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.detail = detail

    def response(self) -> tuple[dict, int]:
        body: dict = {"error": self.code}
        if self.detail:
            body["detail"] = self.detail
        return body, self.status


def parse_body[M: BaseModel](model: type[M]) -> M:
    try:
        data = request.get_json(force=False, silent=False)
    except BadRequest as e:
        raise ApiError(400, "invalid_json") from e
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_json", "expected a JSON object")
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise ApiError(422, "validation_error", _first_error(e)) from e


def _first_error(e: ValidationError) -> str:
    err = e.errors()[0]
    loc = ".".join(str(p) for p in err.get("loc", ()))
    return f"{loc}: {err.get('msg', 'invalid')}".strip(": ")


def client_ip() -> str | None:
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr


def user_agent() -> str | None:
    return request.headers.get("User-Agent", "")[:400] or None
