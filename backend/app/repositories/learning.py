"""Graded reading/typing content + completions + milestone claims.

Content is either bundled (``child_id`` NULL, readable by everyone) or
caregiver-authored for one child. All access is through the caller's client so
RLS scopes it — bundled rows and the caller's own children's rows only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.repositories._base import one_or_none, rows

_READING = "reading_texts"
_WRITING = "writing_prompts"
_ATTEMPTS = "learning_attempts"
_COMPLETIONS = "learning_completions"
_CLAIMS = "learning_reward_claims"

_TABLE = {"reading": _READING, "writing": _WRITING}


def _visible(q, child_id: str):
    # bundled (child_id null) OR this child's own authored rows
    return q.or_(f"child_id.is.null,child_id.eq.{child_id}")


# --- content ---------------------------------------------------------


def list_reading(db: Any, child_id: str, level: int) -> list[dict]:
    q = db.table(_READING).select("id, level, title, body, tts_asset_id, child_id")
    return rows(_visible(q, child_id).eq("level", level).order("child_id").order("id").execute())


def list_writing(db: Any, child_id: str, level: int) -> list[dict]:
    q = db.table(_WRITING).select("id, level, hint, child_id")  # target hidden
    return rows(_visible(q, child_id).eq("level", level).order("child_id").order("id").execute())


def list_tasks(db: Any, kind: str, child_id: str, level: int) -> list[dict]:
    """Every task at a level (bundled + this child's), full fields — for the
    caregiver editor. No completion filter."""
    cols = (
        "id, level, title, body, child_id"
        if kind == "reading"
        else "id, level, hint, target, child_id"
    )
    q = db.table(_TABLE[kind]).select(cols)
    return rows(_visible(q, child_id).eq("level", level).order("child_id").order("id").execute())


def get_reading(db: Any, text_id: str) -> dict | None:
    return one_or_none(db.table(_READING).select("*").eq("id", text_id).execute())


def get_writing(db: Any, prompt_id: str) -> dict | None:
    return one_or_none(db.table(_WRITING).select("*").eq("id", prompt_id).execute())


def create_reading(db: Any, child_id: str, created_by: str, values: dict) -> dict:
    return one_or_none(
        db.table(_READING)
        .insert({"child_id": child_id, "created_by": created_by, **values})
        .execute()
    )


def create_writing(db: Any, child_id: str, created_by: str, values: dict) -> dict:
    return one_or_none(
        db.table(_WRITING)
        .insert({"child_id": child_id, "created_by": created_by, **values})
        .execute()
    )


def delete_task(db: Any, kind: str, task_id: str) -> None:
    # RLS's write policy only allows deleting a row whose child_id is the
    # caller's — bundled rows (child_id null) are untouched.
    db.table(_TABLE[kind]).delete().eq("id", task_id).execute()


# --- attempts / completions -----------------------------------------


def record_attempt(
    db: Any, child_id: str, *, kind: str, ref_id: str, level: int, verdict: str
) -> None:
    db.table(_ATTEMPTS).insert(
        {
            "child_id": child_id,
            "kind": kind,
            "ref_id": ref_id,
            "level": level,
            "verdict": verdict,
            "tokens_awarded": 0,
        }
    ).execute()


def completed_task_ids(db: Any, child_id: str, kind: str, level: int) -> set[str]:
    got = rows(
        db.table(_COMPLETIONS)
        .select("task_id")
        .eq("child_id", child_id)
        .eq("kind", kind)
        .eq("level", level)
        .execute()
    )
    return {r["task_id"] for r in got}


def record_completion(db: Any, child_id: str, task_id: str, kind: str, level: int) -> None:
    # upsert — a second "done" on the same task is a no-op
    db.table(_COMPLETIONS).upsert(
        {"child_id": child_id, "task_id": task_id, "kind": kind, "level": level},
        on_conflict="child_id,task_id",
    ).execute()


def completion_count(db: Any, child_id: str, kind: str, level: int) -> int:
    return len(completed_task_ids(db, child_id, kind, level))


# --- milestone claims ----------------------------------------------


def get_claimed(db: Any, child_id: str, kind: str, level: int) -> int:
    row = one_or_none(
        db.table(_CLAIMS)
        .select("claimed")
        .eq("child_id", child_id)
        .eq("kind", kind)
        .eq("level", level)
        .execute()
    )
    return int(row["claimed"]) if row else 0


def set_claimed(db: Any, child_id: str, kind: str, level: int, claimed: int) -> None:
    db.table(_CLAIMS).upsert(
        {
            "child_id": child_id,
            "kind": kind,
            "level": level,
            "claimed": claimed,
            "updated_at": datetime.now(UTC).isoformat(),
        },
        on_conflict="child_id,kind,level",
    ).execute()


def progress_all(db: Any, child_id: str) -> list[dict]:
    """Per (kind, level) completion + milestone summary — for the caregiver."""
    done = rows(db.table(_COMPLETIONS).select("kind, level").eq("child_id", child_id).execute())
    counts: dict[tuple[str, int], int] = {}
    for r in done:
        counts[(r["kind"], r["level"])] = counts.get((r["kind"], r["level"]), 0) + 1
    out = []
    for (kind, level), completed in sorted(counts.items()):
        claimed = get_claimed(db, child_id, kind, level)
        out.append(
            {
                "kind": kind,
                "level": level,
                "completed": completed,
                "toward_next": completed % 3,
                "unclaimed": completed // 3 - claimed,
            }
        )
    return out
