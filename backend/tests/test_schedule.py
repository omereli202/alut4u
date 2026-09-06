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


def test_apply_template_seeds_day(client, caregiver_mode):
    child_id = _child(client)

    templates = client.get("/api/schedule/templates").get_json()["templates"]
    assert templates, "expected at least one bundled schedule template"
    tpl_id = templates[0]["id"]

    r = client.post(
        "/api/schedule/apply-template",
        json={"child_id": child_id, "template_id": tpl_id, "the_date": DAY},
    )
    assert r.status_code == 201
    created = r.get_json()["created"]
    assert created > 0

    day = client.get(f"/api/schedule/day?child_id={child_id}&date={DAY}").get_json()["items"]
    assert len(day) == created
    assert [i["sort_order"] for i in day] == list(range(created))
    for i in day:
        assert i["tts_asset_id"], f"{i['title']} has no pre-generated audio"
        assert i["is_completed"] is False


def test_apply_template_appends_to_existing_day(client, caregiver_mode):
    child_id = _child(client)
    _item(client, child_id, "משימה קיימת", 0)

    tpl_id = client.get("/api/schedule/templates").get_json()["templates"][0]["id"]
    client.post(
        "/api/schedule/apply-template",
        json={"child_id": child_id, "template_id": tpl_id, "the_date": DAY},
    )

    day = client.get(f"/api/schedule/day?child_id={child_id}&date={DAY}").get_json()["items"]
    assert day[0]["title"] == "משימה קיימת"
    assert [i["sort_order"] for i in day] == list(range(len(day)))


def test_apply_template_unknown_id_404(client, caregiver_mode):
    child_id = _child(client)
    r = client.post(
        "/api/schedule/apply-template",
        json={"child_id": child_id, "template_id": "no-such-template", "the_date": DAY},
    )
    assert r.status_code == 404


def test_apply_template_needs_caregiver_mode(client, caregiver_mode):
    child_id = _child(client)
    tpl_id = client.get("/api/schedule/templates").get_json()["templates"][0]["id"]
    client.delete("/api/auth/pin/elevation")  # → User Mode
    r = client.post(
        "/api/schedule/apply-template",
        json={"child_id": child_id, "template_id": tpl_id, "the_date": DAY},
    )
    assert r.status_code == 403


def test_apply_template_is_tenant_scoped(client, caregiver_mode, app):
    child_id = _child(client)

    other = app.test_client()
    assert (
        other.post(
            "/api/auth/signup",
            json={
                "email": f"tpl-{uuid.uuid4().hex[:10]}@example.com",
                "password": "test-password-123",
                "display_name": "o",
                "accept_terms": True,
            },
        ).status_code
        == 201
    )
    assert other.put("/api/auth/pin", json={"pin": "1357"}).status_code == 204
    assert other.post("/api/auth/pin", json={"pin": "1357"}).status_code == 200  # → Caregiver Mode
    r = other.post(
        "/api/schedule/apply-template",
        json={"child_id": child_id, "template_id": "home-day", "the_date": DAY},
    )
    assert r.status_code == 404


def test_save_template_from_day(client, caregiver_mode):
    child_id = _child(client)
    _item(client, child_id, "ארוחת בוקר", 0)
    _item(client, child_id, "גן", 1)

    r = client.post(
        "/api/schedule/save-template",
        json={"child_id": child_id, "the_date": DAY, "name_he": "היום של דני"},
    )
    assert r.status_code == 201
    tpl_id = r.get_json()["id"]

    listed = client.get("/api/schedule/templates").get_json()["templates"]
    mine = next(t for t in listed if t["id"] == tpl_id)
    assert mine["name_he"] == "היום של דני"
    assert mine["owned"] is True

    applied = client.post(
        "/api/schedule/apply-template",
        json={"child_id": child_id, "template_id": tpl_id, "the_date": NEXT},
    ).get_json()
    assert [i["title"] for i in applied["items"]] == ["ארוחת בוקר", "גן"]


def test_save_template_empty_day_422(client, caregiver_mode):
    child_id = _child(client)
    r = client.post(
        "/api/schedule/save-template",
        json={"child_id": child_id, "the_date": DAY, "name_he": "ריק"},
    )
    assert r.status_code == 422


def test_saved_template_is_private(client, caregiver_mode, app):
    child_id = _child(client)
    _item(client, child_id, "פרטי", 0)
    tpl_id = client.post(
        "/api/schedule/save-template",
        json={"child_id": child_id, "the_date": DAY, "name_he": "שלי"},
    ).get_json()["id"]

    other = app.test_client()
    other.post(
        "/api/auth/signup",
        json={
            "email": f"tpl-{uuid.uuid4().hex[:10]}@example.com",
            "password": "test-password-123",
            "display_name": "o",
            "accept_terms": True,
        },
    )
    other.put("/api/auth/pin", json={"pin": "1357"})
    other.post("/api/auth/pin", json={"pin": "1357"})
    other_child = _child(other)

    listed = other.get("/api/schedule/templates").get_json()["templates"]
    assert tpl_id not in [t["id"] for t in listed]

    r = other.post(
        "/api/schedule/apply-template",
        json={"child_id": other_child, "template_id": tpl_id, "the_date": DAY},
    )
    assert r.status_code == 404


def test_delete_own_template(client, caregiver_mode):
    child_id = _child(client)
    _item(client, child_id, "משימה", 0)
    tpl_id = client.post(
        "/api/schedule/save-template",
        json={"child_id": child_id, "the_date": DAY, "name_he": "למחיקה"},
    ).get_json()["id"]

    assert client.delete(f"/api/schedule/templates/{tpl_id}").status_code == 204
    listed = client.get("/api/schedule/templates").get_json()["templates"]
    assert tpl_id not in [t["id"] for t in listed]


def test_delete_bundled_template_403(client, caregiver_mode):
    assert client.delete("/api/schedule/templates/home-day").status_code == 403


def test_save_template_limit(client, caregiver_mode, monkeypatch):
    from app.api import schedule as schedule_api

    monkeypatch.setattr(schedule_api, "_MAX_SAVED_TEMPLATES", 2)
    child_id = _child(client)
    _item(client, child_id, "משימה", 0)

    for i in range(2):
        assert (
            client.post(
                "/api/schedule/save-template",
                json={"child_id": child_id, "the_date": DAY, "name_he": f"ת{i}"},
            ).status_code
            == 201
        )
    r = client.post(
        "/api/schedule/save-template",
        json={"child_id": child_id, "the_date": DAY, "name_he": "שלישית"},
    )
    assert r.status_code == 409


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
