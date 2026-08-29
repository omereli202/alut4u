from __future__ import annotations

from tests.conftest import requires_supabase

pytestmark = requires_supabase


def _child(client) -> str:
    return client.post("/api/children", json={"name": "ילד", "consent_basis": "parent"}).get_json()[
        "id"
    ]


def _award(client, child_id, amount, reason="עבודה טובה"):
    return client.post(
        "/api/tokens/award", json={"child_id": child_id, "amount": amount, "reason": reason}
    )


def _reward(client, child_id, title, cost):
    return client.post(
        "/api/tokens/rewards", json={"child_id": child_id, "title": title, "cost": cost}
    ).get_json()


def test_rules_crud_with_tts(client, caregiver_mode):
    child_id = _child(client)
    rule = client.post(
        "/api/tokens/rules",
        json={
            "child_id": child_id,
            "title": "מדברים יפה",
            "body": "אנחנו מדברים בקול רגוע",
            "symbol_id": "happy",
        },
    ).get_json()
    assert rule["tts_asset_id"]

    rules = client.get(f"/api/tokens/rules?child_id={child_id}").get_json()["rules"]
    assert [r["title"] for r in rules] == ["מדברים יפה"]

    updated = client.patch(
        f"/api/tokens/rules/{rule['id']}", json={"body": "מדברים ברוגע ובנימוס"}
    ).get_json()
    assert updated["tts_asset_id"] != rule["tts_asset_id"]

    assert client.delete(f"/api/tokens/rules/{rule['id']}").status_code == 204


def test_award_updates_balance_and_ledger(client, caregiver_mode):
    child_id = _child(client)
    assert _award(client, child_id, 5).status_code == 201
    _award(client, child_id, 3)
    _award(client, child_id, -2, reason="תיקון")

    bal = client.get(f"/api/tokens/balance?child_id={child_id}").get_json()
    assert bal["balance"] == 6
    assert len(bal["transactions"]) == 3
    assert bal["transactions"][0]["delta"] == -2  # newest first


def test_redeem_holds_tokens_then_approve(client, caregiver_mode):
    child_id = _child(client)
    _award(client, child_id, 10)
    reward = _reward(client, child_id, "גלידה", 6)

    # child redeems (allowed in User Mode)
    client.delete("/api/auth/pin/elevation")
    r = client.post("/api/tokens/redeem", json={"child_id": child_id, "reward_id": reward["id"]})
    assert r.status_code == 201
    body = r.get_json()
    assert body["redemption"]["status"] == "pending"
    assert body["balance"] == 4  # held immediately

    # caregiver approves
    client.post("/api/auth/pin", json={"pin": "2580"})
    q = client.get("/api/tokens/queue").get_json()["pending"]
    assert len(q) == 1 and q[0]["child_name"] == "ילד"
    approved = client.post(f"/api/tokens/redemptions/{q[0]['id']}/approve").get_json()
    assert approved["redemption"]["status"] == "approved"
    assert approved["balance"] == 4  # unchanged on approve


def test_reject_refunds(client, caregiver_mode):
    child_id = _child(client)
    _award(client, child_id, 10)
    reward = _reward(client, child_id, "מסך", 8)
    red = client.post(
        "/api/tokens/redeem", json={"child_id": child_id, "reward_id": reward["id"]}
    ).get_json()["redemption"]
    assert client.get(f"/api/tokens/balance?child_id={child_id}").get_json()["balance"] == 2

    rejected = client.post(f"/api/tokens/redemptions/{red['id']}/reject").get_json()
    assert rejected["redemption"]["status"] == "rejected"
    assert rejected["balance"] == 10  # refunded

    assert client.post(f"/api/tokens/redemptions/{red['id']}/reject").status_code == 409


def test_redeem_blocked_when_insufficient(client, caregiver_mode):
    child_id = _child(client)
    _award(client, child_id, 3)
    reward = _reward(client, child_id, "יקר", 10)
    r = client.post("/api/tokens/redeem", json={"child_id": child_id, "reward_id": reward["id"]})
    assert r.status_code == 409
    assert r.get_json()["error"] == "insufficient_tokens"


def test_user_mode_cannot_award_or_manage(client, caregiver_mode):
    child_id = _child(client)
    client.delete("/api/auth/pin/elevation")
    assert _award(client, child_id, 5).status_code == 403
    assert (
        client.post(
            "/api/tokens/rewards", json={"child_id": child_id, "title": "x", "cost": 1}
        ).status_code
        == 403
    )
    # reads still fine
    assert client.get(f"/api/tokens/balance?child_id={child_id}").status_code == 200


def test_tokens_tenant_scoped(client, caregiver_mode, app):
    child_id = _child(client)
    _award(client, child_id, 5)
    reward = _reward(client, child_id, "פרס", 3)

    other = app.test_client()
    other.post(
        "/api/auth/signup",
        json={
            "email": f"tok-{child_id[:8]}@example.com",
            "password": "test-password-123",
            "display_name": "o",
            "accept_terms": True,
        },
    )
    other.put("/api/auth/pin", json={"pin": "1470"})
    other.post("/api/auth/pin", json={"pin": "1470"})

    assert other.get(f"/api/tokens/balance?child_id={child_id}").status_code == 404
    assert (
        other.post(
            "/api/tokens/redeem", json={"child_id": child_id, "reward_id": reward["id"]}
        ).status_code
        == 404
    )
    assert other.get("/api/tokens/queue").get_json()["pending"] == []
