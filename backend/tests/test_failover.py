from __future__ import annotations

from tests.conftest import ProviderHTTPError


def test_single_key_failover_uses_key_two(client, provider):
    response = client.post(
        "/chat",
        json={"session_id": "s-failover", "message": "route around key one"},
        headers={"X-Simulate-Failure": "key_1=429"},
    )

    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert metadata["resolution_source"] == "LIVE_INFERENCE"
    assert metadata["key_id"] == "key_2"
    assert metadata["fallback_attempts"] == 1
    assert provider.calls[0]["api_key"] == "test-key-two"
    assert len(provider.calls) == 1


def test_failed_key_is_not_poisoned_for_later_requests(client, provider):
    client.post(
        "/chat",
        json={"session_id": "s-poison-1", "message": "first attempt"},
        headers={"X-Simulate-Failure": "key_1=429"},
    )
    followup = client.post(
        "/chat", json={"session_id": "s-poison-2", "message": "second attempt"}
    )

    metadata = followup.json()["metadata"]
    assert metadata["key_id"] == "key_1"
    assert metadata["fallback_attempts"] == 0
    assert provider.calls[1]["api_key"] == "test-key-one"


def test_all_keys_fail_returns_exact_503_without_writing_history(client, provider):
    response = client.post(
        "/chat",
        json={"session_id": "s-all-fail", "message": "nobody home"},
        headers={"X-Simulate-Failure": "*=429"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "all providers unavailable"}
    assert provider.calls == []
    assert client.get("/sessions/s-all-fail/messages").status_code == 404


def test_multi_key_simulation_exhausts_pool(client, provider):
    response = client.post(
        "/chat",
        json={"session_id": "s-multi-fail", "message": "still nobody home"},
        headers={"X-Simulate-Failure": "key_1=429,key_2=500"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "all providers unavailable"}
    assert provider.calls == []


def test_503_preserves_previous_successful_history(client, provider):
    payload = {"session_id": "s-preserve", "message": "keep me"}
    assert client.post("/chat", json=payload).status_code == 200

    failed = client.post(
        "/chat", json=payload, headers={"X-Simulate-Failure": "*=429"}
    )
    assert failed.status_code == 503

    history = client.get("/sessions/s-preserve/messages").json()["messages"]
    assert [message["role"] for message in history] == ["user", "assistant"]
    assert history[0]["content"] == "keep me"


def test_real_provider_rate_limit_triggers_failover(client, provider):
    provider.failures["test-key-one"] = ProviderHTTPError(429, "rate limited")

    response = client.post(
        "/chat", json={"session_id": "s-real-429", "message": "limited"}
    )

    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert metadata["key_id"] == "key_2"
    assert metadata["fallback_attempts"] == 1


def test_real_provider_outage_exhausts_pool(client, provider):
    provider.failures["test-key-one"] = ProviderHTTPError(500)
    provider.failures["test-key-two"] = ProviderHTTPError(503)

    response = client.post(
        "/chat", json={"session_id": "s-real-5xx", "message": "outage"}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "all providers unavailable"}
    # User message is not persisted for the failed request.
    assert client.get("/sessions/s-real-5xx/messages").status_code == 404


def test_simulation_header_ignored_when_disabled(client_no_simulation, provider):
    response = client_no_simulation.post(
        "/chat",
        json={"session_id": "s-sim-off", "message": "header must be inert"},
        headers={"X-Simulate-Failure": "key_1=429"},
    )

    assert response.status_code == 200
    assert response.json()["metadata"]["key_id"] == "key_1"
    assert response.json()["metadata"]["fallback_attempts"] == 0
