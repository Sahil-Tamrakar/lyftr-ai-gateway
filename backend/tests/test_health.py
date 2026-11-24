from __future__ import annotations


def test_health_reports_keys_and_cache(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "keys_configured": 2,
        "cache_enabled": True,
    }


def test_health_counts_zero_keys_when_unconfigured(tmp_path, monkeypatch, provider):
    from tests.conftest import make_client

    with make_client(tmp_path, monkeypatch, keys="") as test_client:
        response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json()["keys_configured"] == 0


def test_cors_allows_configured_origin_only(client):
    allowed = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"

    blocked = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in blocked.headers
