from __future__ import annotations

from tests.conftest import requires_supabase

pytestmark = requires_supabase

DAY = "2026-09-01"
NEXT = "2026-09-02"


def _child(client) -> str:
    return client.post("/api/children", json={"name": "ילד", "consent_basis": "parent"}).get_json()[
        "id"
    ]


def _item(client, child_id, title, order=0, date=DAY):
    return client.post(
        "/api/schedule/items",
        json={"child_id": child_id, "the_date": date, "title": title, "sort_order": order},
    ).get_json()


def test_build_day_and_read_order(client, caregiver_mode):
    child_id = _child(client)
    _item(client, child_id, "ארוחת בוקר", 0)
    _item(client, child_id, "צחצוח שיניים", 1)
    _item(client, child_id, "גן", 2)

    day = client.get(f"/api/schedule/day?child_id={child_id}&date={DAY}").get_json()["items"]
    assert [i["title"] for i in day] == ["ארוחת בוקר", "צחצוח שיניים", "גן"]
    for i in day:
        assert i["tts_asset_id"], f"{i['title']} has no pre-generated audio"
        assert i["is_completed"] is False


def test_toggle_is_idempotent_and_user_mode_allowed(client, caregiver_mode):
    child_id = _child(client)
    item = _item(client, child_id, "משימה")
    client.delete("/api/auth/pin/elevation")  # → User Mode

    r1 = client.post(
        "/api/schedule/toggle",
        json={"item_id": item["id"], "completed": True, "idempotency_key": "k1"},
    )
    assert r1.status_code == 200
    body1 = r1.get_json()
    assert body1["is_completed"] is True
    assert body1["completed_at"]

    # replay — still done, no error
    r2 = client.post(
        "/api/schedule/toggle",
        json={"item_id": item["id"], "completed": True, "idempotency_key": "k1"},
    )
    assert r2.status_code == 200
    assert r2.get_json()["is_completed"] is True

    undone = client.post(
        "/api/schedule/toggle", json={"item_id": item["id"], "completed": False}
    ).get_json()
    assert undone["is_completed"] is False
    assert undone["completed_at"] is None


def test_reorder_and_edit_regenerates_tts(client, caregiver_mode):
    child_id = _child(client)
    a = _item(client, child_id, "א", 0)
    b = _item(client, child_id, "ב", 1)
    assert (
        client.put(
            "/api/schedule/items/order", json={"child_id": child_id, "order": [b["id"], a["id"]]}
        ).status_code
        == 204
    )
    day = client.get(f"/api/schedule/day?child_id={child_id}&date={DAY}").get_json()["items"]
    assert [i["id"] for i in day] == [b["id"], a["id"]]

    edited = client.patch(f"/api/schedule/items/{a['id']}", json={"title": "אלף"}).get_json()
    assert edited["title"] == "אלף"
    assert edited["tts_asset_id"] != a["tts_asset_id"]


def test_copy_day_resets_completion(client, caregiver_mode):
    child_id = _child(client)
    item = _item(client, child_id, "שגרה")
    client.post("/api/schedule/toggle", json={"item_id": item["id"], "completed": True})

    n = client.post(
        "/api/schedule/copy-day",
        json={"child_id": child_id, "from_date": DAY, "to_date": NEXT},
    ).get_json()["copied"]
    assert n == 1

    copied = client.get(f"/api/schedule/day?child_id={child_id}&date={NEXT}").get_json()["items"]
    assert len(copied) == 1
    assert copied[0]["is_completed"] is False
    assert copied[0]["title"] == "שגרה"


def test_calendar_events(client, caregiver_mode):
    child_id = _child(client)
    ev = client.post(
        "/api/schedule/events",
        json={"child_id": child_id, "event_date": "2026-09-15", "title": "רופא שיניים"},
    ).get_json()
    assert ev["title"] == "רופא שיניים"

    listing = client.get(
        f"/api/schedule/calendar?child_id={child_id}&from=2026-09-01&to=2026-09-30"
    ).get_json()["events"]
    assert [e["title"] for e in listing] == ["רופא שיניים"]

    assert client.delete(f"/api/schedule/events/{ev['id']}").status_code == 204


def test_schedule_writes_need_caregiver_mode(client, signed_up):
    child_id = client.post(
        "/api/children", json={"name": "x", "consent_basis": "parent"}
    )  # not in caregiver mode → this itself 403s
    assert child_id.status_code == 403


def test_schedule_is_tenant_scoped(client, caregiver_mode, app):
    child_id = _child(client)
    item = _item(client, child_id, "פרטי")

    other = app.test_client()
    other.post(
        "/api/auth/signup",
        json={
            "email": f"sch-{child_id[:8]}@example.com",
            "password": "test-password-123",
            "display_name": "o",
            "accept_terms": True,
        },
    )
    assert other.get(f"/api/schedule/day?child_id={child_id}&date={DAY}").status_code == 404
    assert (
        other.post(
            "/api/schedule/toggle", json={"item_id": item["id"], "completed": True}
        ).status_code
        == 404
    )
