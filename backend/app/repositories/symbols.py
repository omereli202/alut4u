"""symbols — global read-only pictogram library.

The bundled library is small (hundreds of rows), so search fetches all and
filters in Python — robust for Hebrew substring matching without wrestling
PostgREST array-filter syntax.
"""

from __future__ import annotations

from functools import lru_cache

from app.repositories._base import one_or_none, rows
from app.services.supabase_client import service_client

_TABLE = "symbols"


def _svc():
    return service_client("read_symbol_library")


@lru_cache(maxsize=1)
def _all() -> tuple[dict, ...]:
    return tuple(rows(_svc().table(_TABLE).select("*").order("id").execute()))


def refresh_cache() -> None:
    _all.cache_clear()


def search(query: str, *, limit: int = 40) -> list[dict]:
    q = (query or "").strip()
    items = _all()
    if not q:
        return list(items[:limit])
    hits = [
        s
        for s in items
        if q in s["id"]
        or q in (s.get("label_he") or "")
        or any(q in kw for kw in s.get("keywords_he") or [])
    ]
    return hits[:limit]


def get(symbol_id: str) -> dict | None:
    return one_or_none(_svc().table(_TABLE).select("*").eq("id", symbol_id).execute())


def exists(symbol_id: str) -> bool:
    return any(s["id"] == symbol_id for s in _all())
