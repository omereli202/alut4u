"""Unit test for symbols._all()'s pagination — no Supabase needed, just a
fake query-builder returning pages. Regression test for the PostgREST
max_rows=1000 truncation bug: an unranged select("*") silently drops
everything past the first 1000 rows (by id), which would 422
`unknown_symbol` for any card whose symbol_id sorts late alphabetically —
exactly the failure mode the Mulberry import (~3,000 rows) would hit."""

from __future__ import annotations

from app.repositories import symbols as repo


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, all_rows):
        self._all_rows = all_rows
        self._range = (0, len(all_rows))

    def table(self, _name):
        return self

    def select(self, _cols):
        return self

    def order(self, _col):
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def execute(self):
        start, end = self._range
        return _FakeResponse(self._all_rows[start : end + 1])


def test_all_pages_past_the_postgrest_row_cap(monkeypatch):
    repo._all.cache_clear()
    fake_rows = [{"id": f"sym-{i:04d}"} for i in range(2500)]
    monkeypatch.setattr(repo, "_svc", lambda: _FakeQuery(fake_rows))
    monkeypatch.setattr(repo, "_PAGE_SIZE", 1000)

    result = repo._all()

    assert len(result) == 2500
    assert result[-1]["id"] == "sym-2499"
    assert repo.exists("sym-2499")
    repo._all.cache_clear()


def test_all_handles_exactly_one_page(monkeypatch):
    repo._all.cache_clear()
    fake_rows = [{"id": f"sym-{i:02d}"} for i in range(10)]
    monkeypatch.setattr(repo, "_svc", lambda: _FakeQuery(fake_rows))
    monkeypatch.setattr(repo, "_PAGE_SIZE", 1000)

    assert len(repo._all()) == 10
    repo._all.cache_clear()
