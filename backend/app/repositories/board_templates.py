"""board_templates — global read-only starter boards, and applying one to a
newly created child (seeds categories + cards, pre-generates their TTS)."""

from __future__ import annotations

from typing import Any

from app.repositories import aac as aac_repo
from app.repositories._base import one_or_none, rows
from app.services.supabase_client import service_client
from app.services.tts import cache as tts_cache

_TABLE = "board_templates"


def _svc():
    return service_client("read_board_templates")


def list_templates() -> list[dict]:
    return rows(
        _svc().table(_TABLE).select("id, name_he, level, description_he").order("level").execute()
    )


def get(template_id: str) -> dict | None:
    return one_or_none(_svc().table(_TABLE).select("*").eq("id", template_id).execute())


def apply_to_child(db: Any, child_id: str, template_id: str) -> None:
    """Seed the child's board from a template. Uses the caregiver's client so
    the new rows pass RLS. Best-effort TTS pre-generation."""
    tpl = get(template_id)
    if not tpl:
        return
    spec = tpl.get("spec") or {}
    for ci, cat in enumerate(spec.get("categories", [])):
        category = aac_repo.create_category(
            db, child_id, name=cat["name"], color=cat.get("color"), sort_order=ci
        )
        for gi, card in enumerate(cat.get("cards", [])):
            tts_text = card.get("tts_text") or card["label"]
            tts_asset_id = tts_cache.ensure_tts_asset(tts_text)
            aac_repo.create_card(
                db,
                child_id,
                {
                    "category_id": category["id"],
                    "label": card["label"],
                    "tts_text": tts_text,
                    "symbol_id": card.get("symbol_id"),
                    "tts_asset_id": tts_asset_id,
                    "grid_order": card.get("grid_order", gi),
                },
            )
