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


def test_daily_bonus_settings(client, caregiver_mode):
    child_id = _child(client)

    # default: no row -> off
    s = client.get(f"/api/tokens/settings?child_id={child_id}").get_json()
    assert s["daily_bonus"] == 0
    assert s["bonus_tts_asset_id"] is None
    assert s["bonus_text"] is None

    # set a bonus -> fixed sentence with the number, TTS pre-generated
    s = client.put("/api/tokens/settings", json={"child_id": child_id, "daily_bonus": 5}).get_json()
    assert s["daily_bonus"] == 5
    assert "5" in s["bonus_text"]
    assert s["bonus_tts_asset_id"]

    # back to 0 clears the audio and the line
    s = client.put("/api/tokens/settings", json={"child_id": child_id, "daily_bonus": 0}).get_json()
    assert s["daily_bonus"] == 0
    assert s["bonus_tts_asset_id"] is None
    assert s["bonus_text"] is None


def test_daily_bonus_user_mode(client, caregiver_mode):
    child_id = _child(client)
    client.put("/api/tokens/settings", json={"child_id": child_id, "daily_bonus": 3})
    client.delete("/api/auth/pin/elevation")
    # child reads the line
    assert client.get(f"/api/tokens/settings?child_id={child_id}").get_json()["daily_bonus"] == 3
    # child cannot change it
    assert (
        client.put(
            "/api/tokens/settings", json={"child_id": child_id, "daily_bonus": 9}
        ).status_code
        == 403
    )


def test_rules_bonus_grant_once_per_day(client, caregiver_mode):
    child_id = _child(client)

    # bonus not configured -> refused
    r = client.post("/api/tokens/rules/bonus", json={"child_id": child_id, "on": "2026-09-06"})
    assert r.status_code == 409 and r.get_json()["error"] == "bonus_disabled"

    client.put("/api/tokens/settings", json={"child_id": child_id, "daily_bonus": 5})

    # first grant of the day
    r = client.post("/api/tokens/rules/bonus", json={"child_id": child_id, "on": "2026-09-06"})
    assert r.status_code == 201
    body = r.get_json()
    assert body["balance"] == 5 and body["bonus_granted_today"] is True

    bal = client.get(f"/api/tokens/balance?child_id={child_id}").get_json()
    assert bal["transactions"][0]["kind"] == "rules_bonus"
    assert bal["transactions"][0]["reason"] == "שמירה על הכללים"

    # settings now reports it granted for that date, but not for another
    s = client.get(f"/api/tokens/settings?child_id={child_id}&on=2026-09-06").get_json()
    assert s["bonus_granted_today"] is True
    s = client.get(f"/api/tokens/settings?child_id={child_id}&on=2026-09-07").get_json()
    assert s["bonus_granted_today"] is False
    # no ?on= -> can't tell
    no_on = client.get(f"/api/tokens/settings?child_id={child_id}").get_json()
    assert no_on["bonus_granted_today"] is None

    # second grant same day -> refused, balance unchanged
    r = client.post("/api/tokens/rules/bonus", json={"child_id": child_id, "on": "2026-09-06"})
    assert r.status_code == 409 and r.get_json()["error"] == "bonus_already_granted"
    assert client.get(f"/api/tokens/balance?child_id={child_id}").get_json()["balance"] == 5

    # a new day -> allowed again
    r = client.post("/api/tokens/rules/bonus", json={"child_id": child_id, "on": "2026-09-07"})
    assert r.status_code == 201 and r.get_json()["balance"] == 10


def test_rules_bonus_requires_caregiver_mode(client, caregiver_mode):
    child_id = _child(client)
    client.put("/api/tokens/settings", json={"child_id": child_id, "daily_bonus": 5})
    client.delete("/api/auth/pin/elevation")
    assert (
        client.post(
            "/api/tokens/rules/bonus", json={"child_id": child_id, "on": "2026-09-06"}
        ).status_code
        == 403
    )


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
