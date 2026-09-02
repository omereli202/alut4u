"""Re-synthesise every stored TTS asset against the configured provider.

Exists for one reason: the shared TTS cache used to be keyed by
sha256(voice|rate|fmt|text), which omitted the provider. Every asset the
silent dev stub ever wrote therefore has *exactly* the digest a real engine
would produce for the same text, and once ``TTSRequest`` started including
``provider`` in the key (see base.py), every row created before that fix
points at an asset that can no longer be found by digest — it just points at
a stub file forever, deaf, unless something walks the tables and repoints it.
That's this module.

Cross-tenant by nature (it must fix every family's cards), operator-initiated,
and offline — run via ``scripts/regenerate_tts.py``, never from a request.
Quota is deliberately NOT charged here: this repairs our own key bug, not
caregiver-initiated usage, and `ensure_tts_asset` only charges a quota inside
a Flask request context anyway (see cache.py's `_caregiver_id`).

Idempotent: once a row's tts_asset_id already resolves to the current
provider's digest, re-running touches neither Azure nor the database for it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.config import Settings, current_settings
from app.repositories import media as media_repo
from app.services import storage
from app.services.supabase_client import service_client
from app.services.tts import get_provider
from app.services.tts.base import TTSRequest
from app.services.tts.cache import ensure_tts_asset

_log = logging.getLogger("app.tts.backfill")

_PAGE_SIZE = 500

# table -> (select columns, fn(row) -> source text or None, tts column to write)
_ROW_TABLES: dict[str, tuple[str, Any, str]] = {
    "aac_cards": (
        "id, label, tts_text, audio_asset_id, tts_asset_id",
        lambda r: (r.get("tts_text") or r.get("label") or "").strip(),
        "tts_asset_id",
    ),
    "schedule_items": (
        "id, title, tts_asset_id",
        lambda r: (r.get("title") or "").strip(),
        "tts_asset_id",
    ),
    "behavior_rules": (
        "id, title, body, audio_asset_id, tts_asset_id",
        lambda r: (r.get("body") or r.get("title") or "").strip(),
        "tts_asset_id",
    ),
}


@dataclass
class Backfill:
    dry_run: bool = True
    provider: str = ""
    scanned: int = 0
    updated: int = 0
    unchanged: int = 0
    warmed: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)  # (table, row_id)
    purged: list[str] = field(default_factory=list)  # media_asset ids


def _paged(table: Any, select: str, size: int = _PAGE_SIZE):
    offset = 0
    while True:
        resp = table.select(select).range(offset, offset + size - 1).execute()
        page = resp.data or []
        yield from page
        if len(page) < size:
            return
        offset += size


def _regenerate_rows(db: Any, table_name: str, b: Backfill, s: Settings) -> None:
    select, text_of, column = _ROW_TABLES[table_name]
    for row in _paged(db.table(table_name), select):
        b.scanned += 1
        if row.get("audio_asset_id"):
            # A caregiver recording outranks TTS (0004_aac.sql) — never touch it.
            continue
        text = text_of(row)
        if not text:
            continue
        req = TTSRequest(text=text, voice=s.azure_speech_voice, provider=b.provider)
        hit = media_repo.find_tts_by_digest(req.cache_key())
        if hit and row.get(column) == hit["id"]:
            b.unchanged += 1
            continue
        asset_id = ensure_tts_asset(text, s)
        if asset_id is None:
            b.failed.append((table_name, row["id"]))
            continue
        if asset_id != row.get(column):
            b.updated += 1
            if not b.dry_run:
                db.table(table_name).update({column: asset_id}).eq("id", row["id"]).execute()
        else:
            b.unchanged += 1


def _regenerate_stories(db: Any, b: Backfill, s: Settings) -> None:
    for row in _paged(db.table("social_stories"), "id, pages"):
        b.scanned += 1
        pages = row.get("pages") or []
        changed = False
        new_pages = []
        for page in pages:
            text = (page.get("text") or "").strip()
            if not text:
                new_pages.append(page)
                continue
            req = TTSRequest(text=text, voice=s.azure_speech_voice, provider=b.provider)
            hit = media_repo.find_tts_by_digest(req.cache_key())
            if hit and page.get("tts_asset_id") == hit["id"]:
                new_pages.append(page)
                continue
            asset_id = ensure_tts_asset(text, s)
            if asset_id is None:
                b.failed.append(("social_stories", row["id"]))
                new_pages.append(page)
                continue
            if asset_id != page.get("tts_asset_id"):
                changed = True
                new_pages.append({**page, "tts_asset_id": asset_id})
            else:
                new_pages.append(page)
        if changed:
            b.updated += 1
            if not b.dry_run:
                db.table("social_stories").update({"pages": new_pages}).eq(
                    "id", row["id"]
                ).execute()
        else:
            b.unchanged += 1


def _warm(texts: list[str], b: Backfill, s: Settings) -> None:
    """Populate the shared digest cache for global, read-only content that has
    no tts_asset_id column of its own — board templates and reading texts.
    Turns their first live use (child-creation seeding; the reading-practice
    GET) from N blocking Azure calls into N cache hits."""
    for raw_text in texts:
        text = (raw_text or "").strip()
        if not text:
            continue
        req = TTSRequest(text=text, voice=s.azure_speech_voice, provider=b.provider)
        if media_repo.find_tts_by_digest(req.cache_key()):
            continue
        if b.dry_run:
            b.warmed += 1
            continue
        asset_id = ensure_tts_asset(text, s)
        if asset_id is None:
            b.failed.append(("warm", text[:40]))
        else:
            b.warmed += 1


def _board_template_texts(db: Any) -> list[str]:
    texts = []
    for tpl in db.table("board_templates").select("spec").execute().data or []:
        spec = tpl.get("spec") or {}
        for cat in spec.get("categories", []):
            for card in cat.get("cards", []):
                texts.append(card.get("tts_text") or card.get("label") or "")
    return texts


def _reading_texts(db: Any) -> list[str]:
    rows = db.table("reading_texts").select("body").execute().data or []
    return [r.get("body") or "" for r in rows]


def _purge_orphans(db: Any, b: Backfill) -> None:
    """Delete now-unreachable silent-stub tts_cache rows + their storage
    objects. Only ever called after a clean regenerate pass (see caller)."""
    referenced: set[str] = set()
    for table_name, (select, _text_of, column) in _ROW_TABLES.items():
        for row in _paged(db.table(table_name), select):
            if row.get(column):
                referenced.add(row[column])
    for row in _paged(db.table("social_stories"), "pages"):
        for page in row.get("pages") or []:
            if page.get("tts_asset_id"):
                referenced.add(page["tts_asset_id"])

    candidates = (
        db.table("media_assets")
        .select("id, storage_path")
        .eq("kind", "tts_cache")
        .eq("mime", "audio/wav")  # the stub's exact, unambiguous fingerprint
        .execute()
        .data
        or []
    )
    for row in candidates:
        if row["id"] in referenced:
            continue
        bucket, _, object_path = row["storage_path"].partition("/")
        storage.remove(bucket, [object_path])
        media_repo.delete(row["id"])
        b.purged.append(row["id"])


def run(
    *,
    dry_run: bool = True,
    purge_orphans: bool = False,
    only: set[str] | None = None,
    allow_silent: bool = False,
    settings: Settings | None = None,
) -> Backfill:
    s = settings or current_settings()
    provider = get_provider(s)
    if provider.name == "silent" and not allow_silent:
        raise RuntimeError(
            "provider is 'silent' — AZURE_SPEECH_KEY is not visible to this "
            "process. Re-running would rewrite every row back to stub audio. "
            "Run via `railway run --service alut4u-backend --environment "
            "<env> -- ...`, or pass allow_silent=True if that's really what "
            "you want."
        )

    b = Backfill(dry_run=dry_run, provider=provider.name)
    db = service_client("regenerate_tts", s)

    tables = only or set(_ROW_TABLES) | {"social_stories"}
    for table_name in _ROW_TABLES:
        if table_name in tables:
            _regenerate_rows(db, table_name, b, s)
    if "social_stories" in tables:
        _regenerate_stories(db, b, s)

    if not only:
        _warm(_board_template_texts(db), b, s)
        _warm(_reading_texts(db), b, s)

    if purge_orphans:
        if b.failed:
            _log.warning(
                "skipping orphan purge — %d row(s) failed to regenerate this run", len(b.failed)
            )
        elif dry_run:
            _log.info("dry run — orphan purge would run here, skipped")
        else:
            _purge_orphans(db, b)

    return b
