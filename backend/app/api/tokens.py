"""Behavior rules, token economy, and the reward store.

One module (``rules_enabled``). Reads and redeeming a reward are allowed in User
Mode; everything else needs Caregiver Mode. Redemption holds the tokens
immediately (a negative transaction) and refunds on rejection.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.api._helpers import ApiError, parse_body
from app.auth.decorators import require_caregiver_mode, require_session
from app.repositories import audit as audit_repo
from app.repositories import children as children_repo
from app.repositories import tokens as repo
from app.schemas.tokens import (
    AwardRequest,
    RedeemRequest,
    ReorderRequest,
    RewardCreate,
    RewardUpdate,
    RuleCreate,
    RuleUpdate,
)
from app.services.tts import cache as tts_cache

bp = Blueprint("tokens", __name__, url_prefix="/api/tokens")


def _own_child_or_404(child_id: str) -> dict:
    child = children_repo.get_child(g.db, child_id)
    if child is None:
        raise ApiError(404, "child_not_found")
    return child


def _arg(name: str) -> str:
    v = request.args.get(name)
    if not v:
        raise ApiError(422, "missing_param", name)
    return v


def _clean(row: dict | None) -> dict | None:
    if row is None:
        return None
    out = {}
    for k, v in row.items():
        if k == "children" and isinstance(v, dict):
            out["child_name"] = v.get("name")
        elif k in {"created_at", "requested_at", "resolved_at"} and v:
            out[k] = str(v)
        else:
            out[k] = v
    return out


# --- behavior rules ---------------------------------------------------


@bp.get("/rules")
@require_session
def list_rules():
    child_id = _arg("child_id")
    _own_child_or_404(child_id)
    return jsonify(rules=[_clean(r) for r in repo.list_rules(g.db, child_id)])


@bp.post("/rules")
@require_caregiver_mode
def create_rule():
    data = parse_body(RuleCreate)
    _own_child_or_404(data.child_id)
    values = {
        "title": data.title,
        "body": data.body,
        "symbol_id": data.symbol_id,
        "icon_asset_id": data.icon_asset_id,
        "sort_order": data.sort_order,
        "tts_asset_id": tts_cache.ensure_tts_asset(data.body or data.title),
    }
    return jsonify(_clean(repo.create_rule(g.db, data.child_id, values))), 201


@bp.patch("/rules/<rule_id>")
@require_caregiver_mode
def update_rule(rule_id: str):
    current = repo.get_rule(g.db, rule_id)
    if current is None:
        raise ApiError(404, "not_found")
    data = parse_body(RuleUpdate)
    patch = data.model_dump(exclude_unset=True)
    values = {
        k: patch[k]
        for k in patch
        if k in {"title", "body", "symbol_id", "icon_asset_id", "audio_asset_id", "sort_order"}
    }
    if "title" in values or "body" in values:
        spoken = (
            values.get("body") or current.get("body") or values.get("title") or current["title"]
        )
        values["tts_asset_id"] = tts_cache.ensure_tts_asset(spoken)
    return jsonify(_clean(repo.update_rule(g.db, rule_id, values)))


@bp.delete("/rules/<rule_id>")
@require_caregiver_mode
def delete_rule(rule_id: str):
    if repo.get_rule(g.db, rule_id) is None:
        raise ApiError(404, "not_found")
    repo.delete_rule(g.db, rule_id)
    return "", 204


@bp.put("/rules/order")
@require_caregiver_mode
def reorder_rules():
    data = parse_body(ReorderRequest)
    _own_child_or_404(data.child_id)
    repo.set_rule_orders(g.db, {r: i for i, r in enumerate(data.order)})
    return "", 204


# --- tokens ---------------------------------------------------------


@bp.get("/balance")
@require_session
def balance():
    child_id = _arg("child_id")
    _own_child_or_404(child_id)
    return jsonify(
        balance=repo.balance(g.db, child_id),
        transactions=[_clean(t) for t in repo.transactions(g.db, child_id)],
    )


@bp.post("/award")
@require_caregiver_mode
def award():
    data = parse_body(AwardRequest)
    _own_child_or_404(data.child_id)
    if data.amount == 0:
        raise ApiError(422, "zero_amount")
    tx = repo.add_transaction(
        g.db,
        data.child_id,
        delta=data.amount,
        kind="award" if data.amount > 0 else "adjustment",
        reason=data.reason,
        created_by=g.caregiver_id,
    )
    audit_repo.log(
        caregiver_id=g.caregiver_id,
        action="token.award",
        target_type="child",
        target_id=data.child_id,
        detail={"amount": data.amount},
    )
    return jsonify(transaction=_clean(tx), balance=repo.balance(g.db, data.child_id)), 201


# --- rewards ------------------------------------------------------


@bp.get("/rewards")
@require_session
def list_rewards():
    child_id = _arg("child_id")
    _own_child_or_404(child_id)
    active_only = request.args.get("all") != "1" or not g.session.is_elevated()
    return jsonify(
        rewards=[_clean(r) for r in repo.list_rewards(g.db, child_id, active_only=active_only)]
    )


@bp.post("/rewards")
@require_caregiver_mode
def create_reward():
    data = parse_body(RewardCreate)
    _own_child_or_404(data.child_id)
    values = {
        "title": data.title,
        "cost": data.cost,
        "symbol_id": data.symbol_id,
        "icon_asset_id": data.icon_asset_id,
        "sort_order": data.sort_order,
    }
    return jsonify(_clean(repo.create_reward(g.db, data.child_id, values))), 201


@bp.patch("/rewards/<reward_id>")
@require_caregiver_mode
def update_reward(reward_id: str):
    if repo.get_reward(g.db, reward_id) is None:
        raise ApiError(404, "not_found")
    data = parse_body(RewardUpdate)
    patch = data.model_dump(exclude_unset=True)
    values = {
        k: patch[k]
        for k in patch
        if k in {"title", "cost", "symbol_id", "icon_asset_id", "is_active", "sort_order"}
    }
    return jsonify(_clean(repo.update_reward(g.db, reward_id, values)))


@bp.delete("/rewards/<reward_id>")
@require_caregiver_mode
def delete_reward(reward_id: str):
    if repo.get_reward(g.db, reward_id) is None:
        raise ApiError(404, "not_found")
    repo.delete_reward(g.db, reward_id)
    return "", 204


@bp.put("/rewards/order")
@require_caregiver_mode
def reorder_rewards():
    data = parse_body(ReorderRequest)
    _own_child_or_404(data.child_id)
    for i, rid in enumerate(data.order):
        repo.update_reward(g.db, rid, {"sort_order": i})
    return "", 204


# --- redemptions -----------------------------------------------


@bp.post("/redeem")
@require_session
def redeem():
    data = parse_body(RedeemRequest)
    _own_child_or_404(data.child_id)
    reward = repo.get_reward(g.db, data.reward_id)
    if reward is None or reward["child_id"] != data.child_id or not reward["is_active"]:
        raise ApiError(404, "reward_not_found")
    if repo.balance(g.db, data.child_id) < reward["cost"]:
        raise ApiError(409, "insufficient_tokens")

    redemption = repo.create_redemption(g.db, data.child_id, reward)
    repo.add_transaction(
        g.db,
        data.child_id,
        delta=-reward["cost"],
        kind="redemption",
        reason=reward["title"],
        created_by=None,
        ref_id=redemption["id"],
    )
    return jsonify(redemption=_clean(redemption), balance=repo.balance(g.db, data.child_id)), 201


@bp.get("/redemptions")
@require_session
def list_redemptions():
    child_id = _arg("child_id")
    _own_child_or_404(child_id)
    return jsonify(redemptions=[_clean(r) for r in repo.list_redemptions_for_child(g.db, child_id)])


@bp.get("/queue")
@require_caregiver_mode
def queue():
    return jsonify(pending=[_clean(r) for r in repo.list_pending_redemptions(g.db)])


@bp.post("/redemptions/<redemption_id>/approve")
@require_caregiver_mode
def approve(redemption_id: str):
    return _resolve(redemption_id, "approved")


@bp.post("/redemptions/<redemption_id>/reject")
@require_caregiver_mode
def reject(redemption_id: str):
    return _resolve(redemption_id, "rejected")


def _resolve(redemption_id: str, status: str):
    red = repo.get_redemption(g.db, redemption_id)
    if red is None:
        raise ApiError(404, "not_found")
    if red["status"] != "pending":
        raise ApiError(409, "already_resolved")

    if status == "rejected":
        repo.add_transaction(
            g.db,
            red["child_id"],
            delta=red["cost"],
            kind="refund",
            reason=f"ביטול: {red['title']}",
            created_by=g.caregiver_id,
            ref_id=red["id"],
        )
    updated = repo.resolve_redemption(g.db, redemption_id, status, g.caregiver_id)
    audit_repo.log(
        caregiver_id=g.caregiver_id,
        action=f"redemption.{status}",
        target_type="redemption",
        target_id=redemption_id,
    )
    return jsonify(redemption=_clean(updated), balance=repo.balance(g.db, red["child_id"]))
