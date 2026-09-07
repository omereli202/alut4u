from __future__ import annotations

import uuid

from tests.conftest import requires_supabase

pytestmark = requires_supabase

DAY = "2026-09-01"
NEXT = "2026-09-02"


def _child(client) -> str:
    return client.post("/api/children", json={"name": "ילד", "consent_basis": "parent"}).get_json()[
        "id"
    ]


def _task(client, child_id, title, *, recurrence="daily", order=0):
    return client.post(
        "/api/tasks/items",
        json={
            "child_id": child_id,
            "title": title,
            "recurrence": recurrence,
            "sort_order": order,
        },
    ).get_json()


def _tick(client, task_id, done=True, date=DAY):
    return client.post(
        "/api/tasks/toggle",
        json={"task_id": task_id, "the_date": date, "completed": done},
    )


def test_module_enabled_by_default(client, caregiver_mode):
    cid = _child(client)
    mods = client.get(f"/api/children/{cid}/modules").get_json()
    assert mods["tasks_enabled"] is True


def test_build_list_and_read_it(client, caregiver_mode):
    cid = _child(client)
    a = _task(client, cid, "לסדר את המיטה", order=0)
    _task(client, cid, "לצחצח שיניים", order=1)
    assert a["tts_asset_id"], "task has no pre-generated audio"

    day = client.get(f"/api/tasks/day?child_id={cid}&date={DAY}").get_json()
    assert [i["title"] for i in day["items"]] == ["לסדר את המיטה", "לצחצח שיניים"]
    assert all(i["is_done"] is False for i in day["items"])
    assert day["reward_tokens"] == 1
    assert day["reward_claimed"] is False
    assert day["all_done"] is False


def test_toggle_is_idempotent_and_user_mode_allowed(client, caregiver_mode):
    cid = _child(client)
    task = _task(client, cid, "משימה")
    client.delete("/api/auth/pin/elevation")  # → User Mode

    r1 = client.post(
        "/api/tasks/toggle",
        json={"task_id": task["id"], "the_date": DAY, "completed": True, "idempotency_key": "k1"},
    )
    assert r1.status_code == 200
    assert r1.get_json()["is_done"] is True

    # replay — still done, no error
    r2 = client.post(
        "/api/tasks/toggle",
        json={"task_id": task["id"], "the_date": DAY, "completed": True, "idempotency_key": "k1"},
    )
    assert r2.status_code == 200
    assert r2.get_json()["is_done"] is True

    undone = _tick(client, task["id"], done=False).get_json()
    assert undone["is_done"] is False


def test_daily_task_resets_next_day_one_off_disappears(client, caregiver_mode):
    cid = _child(client)
    daily = _task(client, cid, "יומית", recurrence="daily", order=0)
    once = _task(client, cid, "חד-פעמית", recurrence="once", order=1)

    _tick(client, daily["id"], date=DAY)
    _tick(client, once["id"], date=DAY)

    today = client.get(f"/api/tasks/day?child_id={cid}&date={DAY}").get_json()
    assert {i["title"]: i["is_done"] for i in today["items"]} == {"יומית": True, "חד-פעמית": True}
    assert today["all_done"] is True

    tomorrow = client.get(f"/api/tasks/day?child_id={cid}&date={NEXT}").get_json()
    assert [i["title"] for i in tomorrow["items"]] == ["יומית"]  # once-task is gone
    assert tomorrow["items"][0]["is_done"] is False  # daily reset


def test_edit_regenerates_tts_and_reorder(client, caregiver_mode):
    cid = _child(client)
    a = _task(client, cid, "א", order=0)
    b = _task(client, cid, "ב", order=1)

    assert (
        client.put(
            "/api/tasks/items/order", json={"child_id": cid, "order": [b["id"], a["id"]]}
        ).status_code
        == 204
    )
    day = client.get(f"/api/tasks/day?child_id={cid}&date={DAY}").get_json()["items"]
    assert [i["id"] for i in day] == [b["id"], a["id"]]

    edited = client.patch(f"/api/tasks/items/{a['id']}", json={"title": "אלף"}).get_json()
    assert edited["title"] == "אלף"
    assert edited["tts_asset_id"] != a["tts_asset_id"]


def test_settings_update(client, caregiver_mode):
    cid = _child(client)
    r = client.put("/api/tasks/settings", json={"child_id": cid, "reward_tokens": 3})
    assert r.status_code == 200
    assert r.get_json()["reward_tokens"] == 3
    assert client.get(f"/api/tasks/day?child_id={cid}&date={DAY}").get_json()["reward_tokens"] == 3

    assert (
        client.put("/api/tasks/settings", json={"child_id": cid, "reward_tokens": 99}).status_code
        == 422
    )


def test_claim_full_flow(client, caregiver_mode):
    cid = _child(client)
    client.put("/api/tasks/settings", json={"child_id": cid, "reward_tokens": 2})
    a = _task(client, cid, "א", order=0)
    b = _task(client, cid, "ב", order=1)

    # not all done yet → 409
    _tick(client, a["id"], date=DAY)
    r = client.post("/api/tasks/claim", json={"child_id": cid, "the_date": DAY})
    assert r.status_code == 409
    assert r.get_json()["error"] == "tasks_incomplete"

    _tick(client, b["id"], date=DAY)
    ok = client.post("/api/tasks/claim", json={"child_id": cid, "the_date": DAY})
    assert ok.status_code == 201
    body = ok.get_json()
    assert body["tokens_awarded"] == 2
    assert body["balance"] == 2

    # second claim same day → 409
    again = client.post("/api/tasks/claim", json={"child_id": cid, "the_date": DAY})
    assert again.status_code == 409
    assert again.get_json()["error"] == "reward_already_granted"

    day = client.get(f"/api/tasks/day?child_id={cid}&date={DAY}").get_json()
    assert day["reward_claimed"] is True


def test_claim_empty_list_409(client, caregiver_mode):
    cid = _child(client)
    r = client.post("/api/tasks/claim", json={"child_id": cid, "the_date": DAY})
    assert r.status_code == 409


def test_claim_needs_caregiver_mode(client, caregiver_mode):
    cid = _child(client)
    a = _task(client, cid, "א")
    _tick(client, a["id"], date=DAY)
    client.delete("/api/auth/pin/elevation")  # → User Mode
    r = client.post("/api/tasks/claim", json={"child_id": cid, "the_date": DAY})
    assert r.status_code == 403


def test_writes_need_caregiver_mode(client, signed_up):
    r = client.post(
        "/api/tasks/items", json={"child_id": "x", "title": "משימה", "recurrence": "daily"}
    )
    assert r.status_code == 403


def test_tasks_are_tenant_scoped(client, caregiver_mode, app):
    cid = _child(client)
    task = _task(client, cid, "פרטי")

    other = app.test_client()
    other.post(
        "/api/auth/signup",
        json={
            "email": f"tsk-{uuid.uuid4().hex[:10]}@example.com",
            "password": "test-password-123",
            "display_name": "o",
            "accept_terms": True,
        },
    )
    assert other.get(f"/api/tasks/day?child_id={cid}&date={DAY}").status_code == 404
    assert (
        other.post(
            "/api/tasks/toggle",
            json={"task_id": task["id"], "the_date": DAY, "completed": True},
        ).status_code
        == 404
    )
