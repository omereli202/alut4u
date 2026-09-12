from __future__ import annotations

from tests.conftest import requires_supabase

pytestmark = requires_supabase


def _child(client, template=None) -> str:
    body = {"name": "ילד", "consent_basis": "parent"}
    if template:
        body["board_template_id"] = template
    return client.post("/api/children", json=body).get_json()["id"]


def test_board_template_seeds_categories_cards_and_tts(client, caregiver_mode):
    child_id = _child(client, template="basic-needs")
    board = client.get(f"/api/aac/board?child_id={child_id}").get_json()

    assert [c["name"] for c in board["categories"]] == ["אוכל", "רגשות", "פעילויות"]
    # 20 core words on the home page (category_id null) + 6 + 4 + 4 in the
    # three topic folders.
    assert len(board["cards"]) == 34
    root_cards = [c for c in board["cards"] if c["category_id"] is None]
    assert len(root_cards) == 20
    for card in board["cards"]:
        assert card["symbol_id"]
        assert card["tts_asset_id"], f"{card['label']} has no pre-generated audio"
        assert card["part_of_speech"], f"{card['label']} has no part_of_speech"


def test_card_lifecycle_and_tts_regen(client, caregiver_mode):
    child_id = _child(client)
    cat = client.post("/api/aac/categories", json={"child_id": child_id, "name": "כללי"}).get_json()

    created = client.post(
        "/api/aac/cards",
        json={"child_id": child_id, "label": "מים", "symbol_id": "drink", "category_id": cat["id"]},
    ).get_json()
    assert created["tts_text"] == "מים"
    first_audio = created["tts_asset_id"]
    assert first_audio

    updated = client.patch(f"/api/aac/cards/{created['id']}", json={"label": "מים קרים"}).get_json()
    assert updated["tts_text"] == "מים קרים"
    assert updated["tts_asset_id"] != first_audio  # regenerated

    assert client.delete(f"/api/aac/cards/{created['id']}").status_code == 204
    assert client.get(f"/api/aac/cards/{created['id']}").status_code == 404


def test_reorder_cards(client, caregiver_mode):
    child_id = _child(client)
    ids = [
        client.post("/api/aac/cards", json={"child_id": child_id, "label": f"c{i}"}).get_json()[
            "id"
        ]
        for i in range(3)
    ]
    reversed_ids = list(reversed(ids))
    assert (
        client.put(
            "/api/aac/cards/order", json={"child_id": child_id, "order": reversed_ids}
        ).status_code
        == 204
    )
    board = client.get(f"/api/aac/board?child_id={child_id}").get_json()
    assert [c["id"] for c in board["cards"]] == reversed_ids


def test_unknown_symbol_rejected(client, caregiver_mode):
    child_id = _child(client)
    r = client.post(
        "/api/aac/cards", json={"child_id": child_id, "label": "x", "symbol_id": "not-real"}
    )
    assert r.status_code == 422
    assert r.get_json()["error"] == "unknown_symbol"


def test_writes_need_caregiver_mode_reads_dont(client, caregiver_mode):
    child_id = _child(client, template="first-words")
    client.delete("/api/auth/pin/elevation")  # → User Mode

    assert client.get(f"/api/aac/board?child_id={child_id}").status_code == 200
    assert (
        client.post("/api/aac/cards", json={"child_id": child_id, "label": "x"}).status_code == 403
    )


def test_aac_is_tenant_scoped(client, caregiver_mode, app):
    child_id = _child(client, template="first-words")
    card_id = client.get(f"/api/aac/board?child_id={child_id}").get_json()["cards"][0]["id"]

    other = app.test_client()
    other.post(
        "/api/auth/signup",
        json={
            "email": f"aac-{child_id[:8]}@example.com",
            "password": "test-password-123",
            "display_name": "o",
            "accept_terms": True,
        },
    )
    other.put("/api/auth/pin", json={"pin": "1379"})
    other.post("/api/auth/pin", json={"pin": "1379"})

    assert other.get(f"/api/aac/board?child_id={child_id}").status_code == 404
    assert other.get(f"/api/aac/cards/{card_id}").status_code == 404
    assert other.patch(f"/api/aac/cards/{card_id}", json={"label": "hijack"}).status_code == 404


def _cat(client, child_id, name, **extra):
    return client.post(
        "/api/aac/categories", json={"child_id": child_id, "name": name, **extra}
    ).get_json()


def test_nested_categories_in_board(client, caregiver_mode):
    child_id = _child(client)
    food = _cat(client, child_id, "אוכל", symbol_id="eat")
    breakfast = _cat(client, child_id, "ארוחת בוקר", parent_id=food["id"])
    assert breakfast["parent_id"] == food["id"]

    card = client.post(
        "/api/aac/cards",
        json={"child_id": child_id, "label": "לחם", "category_id": breakfast["id"]},
    ).get_json()

    board = client.get(f"/api/aac/board?child_id={child_id}").get_json()
    by_name = {c["name"]: c for c in board["categories"]}
    assert by_name["אוכל"]["parent_id"] is None
    assert by_name["אוכל"]["symbol_id"] == "eat"
    assert by_name["ארוחת בוקר"]["parent_id"] == food["id"]
    saved = next(c for c in board["cards"] if c["id"] == card["id"])
    assert saved["category_id"] == breakfast["id"]


def test_category_parent_must_be_same_child(client, caregiver_mode, app):
    child_a = _child(client)
    child_b = _child(client)
    b_cat = _cat(client, child_b, "של ב")

    # another child of the same caregiver
    r = client.post(
        "/api/aac/categories",
        json={"child_id": child_a, "name": "x", "parent_id": b_cat["id"]},
    )
    assert r.status_code == 422
    assert r.get_json()["error"] == "bad_parent"

    # another caregiver's category id
    other = app.test_client()
    other.post(
        "/api/auth/signup",
        json={
            "email": f"catp-{child_a[:8]}@example.com",
            "password": "test-password-123",
            "display_name": "o",
            "accept_terms": True,
        },
    )
    other.put("/api/auth/pin", json={"pin": "1379"})
    other.post("/api/auth/pin", json={"pin": "1379"})
    other_child = _child(other)
    other_cat = _cat(other, other_child, "זר")
    r = client.post(
        "/api/aac/categories",
        json={"child_id": child_a, "name": "x", "parent_id": other_cat["id"]},
    )
    assert r.status_code == 422
    assert r.get_json()["error"] == "bad_parent"


def test_category_cycle_rejected(client, caregiver_mode):
    child_id = _child(client)
    a = _cat(client, child_id, "א")
    b = _cat(client, child_id, "ב", parent_id=a["id"])
    r = client.patch(f"/api/aac/categories/{a['id']}", json={"parent_id": b["id"]})
    assert r.status_code == 422
    assert r.get_json()["error"] == "category_cycle"


def test_nesting_depth_capped_at_four(client, caregiver_mode):
    child_id = _child(client)
    parent = None
    ids = []
    for i in range(4):  # levels 1..4 are fine
        kw = {"parent_id": parent} if parent else {}
        cat = _cat(client, child_id, f"רמה {i}", **kw)
        assert "id" in cat, cat
        ids.append(cat["id"])
        parent = cat["id"]

    r = client.post(
        "/api/aac/categories",
        json={"child_id": child_id, "name": "רמה 5", "parent_id": parent},
    )
    assert r.status_code == 422
    assert r.get_json()["error"] == "too_deep"

    # moving the level-1 root under the level-4 leaf would make a 5+-deep tree
    r = client.patch(f"/api/aac/categories/{ids[0]}", json={"parent_id": ids[3]})
    assert r.status_code == 422


def test_delete_parent_floats_children_up(client, caregiver_mode):
    child_id = _child(client)
    food = _cat(client, child_id, "אוכל")
    breakfast = _cat(client, child_id, "ארוחת בוקר", parent_id=food["id"])
    card = client.post(
        "/api/aac/cards",
        json={"child_id": child_id, "label": "לחם", "category_id": food["id"]},
    ).get_json()

    assert client.delete(f"/api/aac/categories/{food['id']}").status_code == 204

    board = client.get(f"/api/aac/board?child_id={child_id}").get_json()
    assert next(c for c in board["categories"] if c["id"] == breakfast["id"])["parent_id"] is None
    assert next(c for c in board["cards"] if c["id"] == card["id"])["category_id"] is None


def test_category_one_visual_enforced(client, caregiver_mode):
    child_id = _child(client)
    r = client.post(
        "/api/aac/categories",
        json={"child_id": child_id, "name": "x", "symbol_id": "eat", "icon_asset_id": "whatever"},
    )
    assert r.status_code == 422


def test_full_board_template_seeds_nested_branch(client, caregiver_mode):
    child_id = _child(client, template="full-board")
    board = client.get(f"/api/aac/board?child_id={child_id}").get_json()
    by_name = {c["name"]: c for c in board["categories"]}

    # Seven top-level topic folders, plus אוכל's two nested sub-categories.
    assert {c["name"] for c in board["categories"] if c["parent_id"] is None} == {
        "אוכל",
        "רגשות",
        "אנשים",
        "מקומות",
        "פעילויות",
        "גוף וכאב",
        "בגדים",
    }
    assert by_name["פירות"]["parent_id"] == by_name["אוכל"]["id"]
    assert by_name["ירקות"]["parent_id"] == by_name["אוכל"]["id"]
    fruit_id = by_name["פירות"]["id"]
    assert {c["label"] for c in board["cards"] if c["category_id"] == fruit_id} == {"תפוח", "בננה"}

    colours = [by_name[n]["color"] for n in ("רגשות", "אוכל", "פירות", "ירקות", "אנשים", "מקומות")]
    assert all(colours) and len(set(colours)) == len(colours)  # each distinct

    # 18 core words sit on the home page (category_id null), colour-coded by
    # part of speech rather than by category — capped so 18 words + 7 folders
    # keeps the home page at 25 tiles total.
    root_cards = [c for c in board["cards"] if c["category_id"] is None]
    root_categories = [c for c in board["categories"] if c["parent_id"] is None]
    assert len(root_cards) == 18
    assert len(root_categories) + len(root_cards) == 25  # the home-page cap
    assert all(c["part_of_speech"] for c in root_cards)

    # Words cut from the home page to make room still ship, moved into the
    # topic folder they fit thematically — and keep their own colour there.
    moved = {
        "חם": "רגשות",
        "קר": "רגשות",
        "מי": "אנשים",
        "איפה": "מקומות",
        "גדול": "בגדים",
        "קטן": "בגדים",
    }
    label_to_card = {c["label"]: c for c in board["cards"]}
    for label, folder in moved.items():
        assert label_to_card[label]["category_id"] == by_name[folder]["id"]
        assert label_to_card[label]["part_of_speech"]


def test_new_category_gets_a_distinct_colour(client, caregiver_mode):
    child_id = _child(client)
    a = _cat(client, child_id, "א")
    b = _cat(client, child_id, "ב")
    assert a["color"] and b["color"]
    assert a["color"] != b["color"]

    # an explicit colour is honoured
    c = _cat(client, child_id, "ג", color="#123456")
    assert c["color"] == "#123456"


def test_category_writes_are_tenant_scoped(client, caregiver_mode, app):
    child_id = _child(client)
    cat_id = _cat(client, child_id, "שלי")["id"]

    other = app.test_client()
    other.post(
        "/api/auth/signup",
        json={
            "email": f"catw-{child_id[:8]}@example.com",
            "password": "test-password-123",
            "display_name": "o",
            "accept_terms": True,
        },
    )
    other.put("/api/auth/pin", json={"pin": "1379"})
    other.post("/api/auth/pin", json={"pin": "1379"})

    assert other.patch(f"/api/aac/categories/{cat_id}", json={"name": "hijack"}).status_code == 404
    assert other.delete(f"/api/aac/categories/{cat_id}").status_code == 404


def test_symbol_search_hebrew(client, signed_up):
    hits = client.get("/api/symbols?q=%D7%9C%D7%90%D7%9B%D7%95%D7%9C").get_json()[
        "symbols"
    ]  # לאכול
    assert any(s["id"] == "eat" for s in hits)
    assert len(client.get("/api/symbols").get_json()["symbols"]) >= 30
