"""symbols — global read-only pictogram library.

Search fetches all rows and filters in Python — robust for Hebrew substring
matching without wrestling PostgREST array-filter syntax, and the library is
small enough in absolute terms (thousands, not millions) for this to stay
cheap. It does mean _all() must page past PostgREST's default max_rows (1000,
see supabase/config.toml) — an unranged select silently truncates past that,
which would 422 `unknown_symbol` for every card using a later-sorting id.

Ranking (lexical tiers + a fastText semantic backfill) lives in
``services.symbol_search``; this module just owns the cached table snapshot and
the derived search index.
"""

from __future__ import annotations

from functools import lru_cache

from app.repositories._base import one_or_none, rows
from app.services import symbol_search as ss
from app.services.supabase_client import service_client

_TABLE = "symbols"
_PAGE_SIZE = 1000


def _svc():
    return service_client("read_symbol_library")


@lru_cache(maxsize=1)
def _all() -> tuple[dict, ...]:
    out: list[dict] = []
    start = 0
    while True:
        page = rows(
            _svc()
            .table(_TABLE)
            .select("*")
            .order("id")
            .range(start, start + _PAGE_SIZE - 1)
            .execute()
        )
        out.extend(page)
        if len(page) < _PAGE_SIZE:
            return tuple(out)
        start += _PAGE_SIZE


@lru_cache(maxsize=1)
def _index() -> ss.Index:
    """The searchable index over the table snapshot — the per-row Hebrew
    normalisation (~1,000 rows × normalize/declitic/haser) done once per worker
    instead of per keystroke across six pickers."""
    return ss.build_index(_all())


def refresh_cache() -> None:
    _all.cache_clear()
    _index.cache_clear()
    ss.reset_cache()


def search(query: str, *, limit: int = 60) -> tuple[list[dict], int]:
    """Return (page, total_matches). See ``services.symbol_search`` for the
    tiering."""
    return ss.search(_index(), query, limit=limit)


def get(symbol_id: str) -> dict | None:
    return one_or_none(_svc().table(_TABLE).select("*").eq("id", symbol_id).execute())


def exists(symbol_id: str) -> bool:
    return any(s["id"] == symbol_id for s in _all())
