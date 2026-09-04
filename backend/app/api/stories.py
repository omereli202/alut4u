"""AI social stories.

The caregiver chats with an agent crew (``/chat``) which interviews them, then
``/compose`` turns the conversation into a structured, SLP-reviewed story and
saves it *with its text and read-aloud audio immediately*. Illustrations are
generated afterwards, one page per request (``/<id>/illustrate``), so composing
returns in seconds and never blocks on a slow image model. The child reads
finished stories in User Mode. AI work counts against the caregiver's monthly
quota.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.api._helpers import ApiError, parse_body
from app.auth.decorators import require_caregiver_mode, require_session
from app.extensions import limiter
from app.repositories import audit as audit_repo
from app.repositories import children as children_repo
from app.repositories import media as media_repo
from app.repositories import stories as repo
from app.schemas.stories import ChatRequest, ComposeRequest, IllustrateRequest
from app.services import storage
from app.services.ai import get_story_ai
from app.services.ai.base import AIError
from app.services.quotas import QuotaExceeded, check, record
from app.services.tts import cache as tts_cache

bp = Blueprint("stories", __name__, url_prefix="/api/stories")

_MAX_PAGES = 8
# Three chat calls (writer + reviewer + illustrator); a generous flat estimate
# used only for the pre-flight check and as a fallback if usage isn't reported.
_COMPOSE_TOKEN_BUDGET = 9000


def _own_child_or_404(child_id: str) -> dict:
    child = children_repo.get_child(g.db, child_id)
    if child is None:
        raise ApiError(404, "child_not_found")
    return child


def _messages(models) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in models]


@bp.post("/chat")
@require_caregiver_mode
@limiter.limit("40 per hour")
def chat():
    data = parse_body(ChatRequest)
    _own_child_or_404(data.child_id)
    try:
        turn = get_story_ai().interview(_messages(data.messages))
    except AIError as e:
        raise ApiError(502, "ai_unavailable", str(e)) from e
    if turn.llm_tokens:
        record(g.caregiver_id, llm_tokens=turn.llm_tokens)
    return jsonify(reply=turn.reply, ready=turn.ready, slots=turn.slots.as_dict())


@bp.post("/compose")
@require_caregiver_mode
@limiter.limit("15 per hour; 40 per day")
def compose():
    data = parse_body(ComposeRequest)
    _own_child_or_404(data.child_id)

    try:
        check(g.caregiver_id, llm_tokens=_COMPOSE_TOKEN_BUDGET)
    except QuotaExceeded as e:
        raise ApiError(429, "quota_exceeded", e.resource) from e

    try:
        story = get_story_ai().compose(_messages(data.messages))
    except AIError as e:
        raise ApiError(502, "ai_unavailable", str(e)) from e

    pages = [
        {
            "text": page.text,
            "image_prompt": page.image_prompt,
            "sentence_type": page.sentence_type,
            "image_asset_id": None,
            "tts_asset_id": tts_cache.ensure_tts_asset(page.text),
        }
        for page in story.pages[:_MAX_PAGES]
    ]

    row = repo.create_story(
        g.db,
        data.child_id,
        {
            "title": story.title,
            "protagonist": story.protagonist,
            "situation": story.situation,
            "schedule": story.schedule or None,
            "goal": story.goal,
            "pages": pages,
            "character_sheet": story.character_sheet or None,
            "review_notes": list(story.review_notes),
            "created_by": g.caregiver_id,
        },
    )
    record(g.caregiver_id, llm_tokens=story.llm_tokens or _COMPOSE_TOKEN_BUDGET)
    audit_repo.log(
        caregiver_id=g.caregiver_id,
        action="story.compose",
        target_type="social_story",
        target_id=row["id"],
    )
    return jsonify(_story_out(row, revised=story.revised)), 201


@bp.post("/<story_id>/illustrate")
@require_caregiver_mode
@limiter.limit("60 per hour; 300 per day")
def illustrate(story_id: str):
    data = parse_body(IllustrateRequest)
    row = repo.get_story(g.db, story_id)
    if row is None:
        raise ApiError(404, "not_found")

    pages = row["pages"]
    idx = data.page_index
    if idx is None:
        idx = next((i for i, p in enumerate(pages) if not p.get("image_asset_id")), None)
        if idx is None:
            return jsonify(_story_out(row))  # nothing left to illustrate
    if idx >= len(pages):
        raise ApiError(422, "page_out_of_range")
    if pages[idx].get("image_asset_id"):
        raise ApiError(409, "already_illustrated")

    try:
        check(g.caregiver_id, images=1)
    except QuotaExceeded as e:
        raise ApiError(429, "quota_exceeded", e.resource) from e

    ai = get_story_ai()
    try:
        img, mime = ai.illustrate(
            pages[idx]["image_prompt"],
            row.get("protagonist") or "",
            character_sheet=row.get("character_sheet") or "",
            reference_image=_reference_image(pages),
        )
    except AIError as e:
        raise ApiError(502, "ai_unavailable", str(e)) from e

    asset_id = repo.store_page_image(row["child_id"], img, mime)
    updated = repo.set_page_image(g.db, story_id, idx, asset_id)
    if updated is None:
        # Someone illustrated this page between our read and write. The image was
        # generated and billed upstream, so we still record it; return the winner.
        record(g.caregiver_id, images=1)
        fresh = repo.get_story(g.db, story_id)
        return jsonify(_story_out(fresh or row)), 200

    record(g.caregiver_id, images=1)
    out = _story_out(updated)
    page = out["pages"][idx]
    return jsonify(page_index=idx, image_url=page["image_url"], art=out["art"]), 200


@bp.get("")
@require_session
def list_stories():
    child_id = request.args.get("child_id")
    if not child_id:
        raise ApiError(422, "missing_param", "child_id")
    _own_child_or_404(child_id)
    return jsonify(
        stories=[
            {
                "id": s["id"],
                "title": s["title"],
                "art": _art_summary(s.get("pages") or []),
                "created_at": str(s["created_at"]),
            }
            for s in repo.list_stories(g.db, child_id)
        ]
    )


@bp.get("/<story_id>")
@require_session
def get_story(story_id: str):
    row = repo.get_story(g.db, story_id)
    if row is None:
        raise ApiError(404, "not_found")
    return jsonify(_story_out(row))


@bp.delete("/<story_id>")
@require_caregiver_mode
def delete_story(story_id: str):
    if repo.get_story(g.db, story_id) is None:
        raise ApiError(404, "not_found")
    repo.delete_story(g.db, story_id)
    return "", 204


def _reference_image(pages: list[dict]) -> tuple[bytes, str] | None:
    """The bytes+mime of the first already-drawn page, so the image model keeps
    the same character. None when no page has art yet (the first illustration)."""
    done = next((p for p in pages if p.get("image_asset_id")), None)
    if done is None:
        return None
    asset = media_repo.get_for_caller(g.db, done["image_asset_id"])
    if asset is None:
        return None
    bucket, _, object_path = asset["storage_path"].partition("/")
    try:
        return storage.download(bucket, object_path), asset["mime"]
    except Exception:  # missing object / storage hiccup — fall back to sheet-only
        return None


def _art_summary(pages: list[dict]) -> dict:
    pending = [i for i, p in enumerate(pages) if not p.get("image_asset_id")]
    return {
        "total": len(pages),
        "illustrated": len(pages) - len(pending),
        "pending_pages": pending,
    }


def _story_out(row: dict, *, revised: bool = False) -> dict:
    pages = row["pages"]
    return {
        "id": row["id"],
        "title": row["title"],
        "protagonist": row.get("protagonist"),
        "situation": row.get("situation"),
        "schedule": row.get("schedule"),
        "goal": row.get("goal"),
        "pages": [
            {
                "text": p["text"],
                "sentence_type": p.get("sentence_type", "descriptive"),
                "image_url": f"/api/media/{p['image_asset_id']}"
                if p.get("image_asset_id")
                else None,
                "audio_url": f"/api/media/{p['tts_asset_id']}" if p.get("tts_asset_id") else None,
            }
            for p in pages
        ],
        "review_notes": row.get("review_notes") or [],
        "revised": revised,
        "art": _art_summary(pages),
        "created_at": str(row["created_at"]),
    }
