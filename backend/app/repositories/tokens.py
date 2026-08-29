"""behavior_rules + token economy + rewards. Via the caller's client (RLS)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.repositories._base import one_or_none, rows

_RULES = "behavior_rules"
_TX = "token_transactions"
_BAL = "token_balances"
_REWARDS = "rewards"
_REDEMPTIONS = "reward_redemptions"

_RULE_FIELDS = (
    "id, child_id, title, body, symbol_id, icon_asset_id, audio_asset_id, "
    "tts_asset_id, sort_order, created_at"
)
_REWARD_FIELDS = (
    "id, child_id, title, cost, symbol_id, icon_asset_id, is_active, sort_order, created_at"
)
_REDEMPTION_FIELDS = (
    "id, child_id, reward_id, title, cost, status, requested_at, resolved_at, resolved_by"
)


# --- behavior rules ------------------------------------------------------


def list_rules(db: Any, child_id: str) -> list[dict]:
    return rows(
        db.table(_RULES).select(_RULE_FIELDS).eq("child_id", child_id).order("sort_order").execute()
    )


def get_rule(db: Any, rule_id: str) -> dict | None:
    return one_or_none(db.table(_RULES).select(_RULE_FIELDS).eq("id", rule_id).execute())


def create_rule(db: Any, child_id: str, values: dict) -> dict:
    return one_or_none(db.table(_RULES).insert({"child_id": child_id, **values}).execute())


def update_rule(db: Any, rule_id: str, values: dict) -> dict | None:
    if not values:
        return get_rule(db, rule_id)
    return one_or_none(db.table(_RULES).update(values).eq("id", rule_id).execute())


def delete_rule(db: Any, rule_id: str) -> None:
    db.table(_RULES).delete().eq("id", rule_id).execute()


def set_rule_orders(db: Any, id_to_order: dict[str, int]) -> None:
    for rid, order in id_to_order.items():
        db.table(_RULES).update({"sort_order": order}).eq("id", rid).execute()


# --- tokens ------------------------------------------------------------


def balance(db: Any, child_id: str) -> int:
    row = one_or_none(db.table(_BAL).select("balance").eq("child_id", child_id).execute())
    return int(row["balance"]) if row else 0


def transactions(db: Any, child_id: str, *, limit: int = 50) -> list[dict]:
    return rows(
        db.table(_TX)
        .select("id, delta, kind, reason, ref_id, created_at")
        .eq("child_id", child_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )


def add_transaction(
    db: Any,
    child_id: str,
    *,
    delta: int,
    kind: str,
    reason: str | None,
    created_by: str | None,
    ref_id: str | None = None,
) -> dict:
    return one_or_none(
        db.table(_TX)
        .insert(
            {
                "child_id": child_id,
                "delta": delta,
                "kind": kind,
                "reason": reason,
                "ref_id": ref_id,
                "created_by": created_by,
            }
        )
        .execute()
    )


# --- rewards ----------------------------------------------------------


def list_rewards(db: Any, child_id: str, *, active_only: bool = True) -> list[dict]:
    q = db.table(_REWARDS).select(_REWARD_FIELDS).eq("child_id", child_id).order("sort_order")
    if active_only:
        q = q.eq("is_active", True)
    return rows(q.execute())


def get_reward(db: Any, reward_id: str) -> dict | None:
    return one_or_none(db.table(_REWARDS).select(_REWARD_FIELDS).eq("id", reward_id).execute())


def create_reward(db: Any, child_id: str, values: dict) -> dict:
    return one_or_none(db.table(_REWARDS).insert({"child_id": child_id, **values}).execute())


def update_reward(db: Any, reward_id: str, values: dict) -> dict | None:
    if not values:
        return get_reward(db, reward_id)
    return one_or_none(db.table(_REWARDS).update(values).eq("id", reward_id).execute())


def delete_reward(db: Any, reward_id: str) -> None:
    db.table(_REWARDS).delete().eq("id", reward_id).execute()


# --- redemptions ----------------------------------------------------


def get_redemption(db: Any, redemption_id: str) -> dict | None:
    return one_or_none(
        db.table(_REDEMPTIONS).select(_REDEMPTION_FIELDS).eq("id", redemption_id).execute()
    )


def create_redemption(db: Any, child_id: str, reward: dict) -> dict:
    return one_or_none(
        db.table(_REDEMPTIONS)
        .insert(
            {
                "child_id": child_id,
                "reward_id": reward["id"],
                "title": reward["title"],
                "cost": reward["cost"],
                "status": "pending",
            }
        )
        .execute()
    )


def list_redemptions_for_child(db: Any, child_id: str, *, limit: int = 30) -> list[dict]:
    return rows(
        db.table(_REDEMPTIONS)
        .select(_REDEMPTION_FIELDS)
        .eq("child_id", child_id)
        .order("requested_at", desc=True)
        .limit(limit)
        .execute()
    )


def list_pending_redemptions(db: Any) -> list[dict]:
    """All pending redemptions across the caregiver's children (RLS scopes it)."""
    return rows(
        db.table(_REDEMPTIONS)
        .select(_REDEMPTION_FIELDS + ", children(name)")
        .eq("status", "pending")
        .order("requested_at")
        .execute()
    )


def resolve_redemption(db: Any, redemption_id: str, status: str, caregiver_id: str) -> dict | None:
    return one_or_none(
        db.table(_REDEMPTIONS)
        .update(
            {
                "status": status,
                "resolved_at": datetime.now(UTC).isoformat(),
                "resolved_by": caregiver_id,
            }
        )
        .eq("id", redemption_id)
        .execute()
    )
