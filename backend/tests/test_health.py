from __future__ import annotations


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert body["env"] == "test"


def test_deep_health_unconfigured_supabase_is_degraded(client):
    r = client.get("/api/health?deep=1")
    assert r.status_code == 503
    assert r.get_json()["checks"]["supabase"] == "unconfigured"


def test_unknown_api_route_is_json_404(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert r.get_json()["error"] == "not_found"


def test_frontend_fallback_serves_index(client):
    r = client.get("/some/spa/route")
    assert r.status_code == 200
    assert b"<!doctype html>" in r.data.lower()
