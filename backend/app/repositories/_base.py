"""Shared helpers for the repository layer."""

from __future__ import annotations

from typing import Any


def one_or_none(resp: Any) -> dict | None:
    rows = getattr(resp, "data", None) or []
    return rows[0] if rows else None


def rows(resp: Any) -> list[dict]:
    return getattr(resp, "data", None) or []
