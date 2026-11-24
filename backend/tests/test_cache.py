from __future__ import annotations


def test_identical_requests_across_sessions_hit_cache(client, provider):
    payload = {
        "session_id": "s-cache-a",
        "message": "What is 2 + 2?",
        "system_prompt": "Answer briefly.",
    }
    first = client.post("/chat", json=payload)
    assert first.status_code == 200
    assert first.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert len(provider.calls) == 1

    cached = client.post("/chat", json={**payload, "session_id": "s-cache-b"})
    assert cached.status_code == 200
    body = cached.json()
    assert body["reply"] == first.json()["reply"]

    metadata = body["metadata"]
    assert metadata["resolution_source"] == "LLM_CACHE"
    assert metadata["key_id"] is None
    assert metadata["fallback_attempts"] == 0
    assert metadata["input_tokens"] == 42
    assert metadata["output_tokens"] == 9
    assert metadata["model"] == "gemini/gemini-2.0-flash"
    assert isinstance(metadata["latency_ms"], int)

    # No additional upstream call was made.
    assert len(provider.calls) == 1


def test_same_session_repeat_is_a_miss_because_history_changed(client, provider):
    payload = {"session_id": "s-cache-history", "message": "hello"}
    first = client.post("/chat", json=payload)
    second = client.post("/chat", json=payload)

    assert first.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert second.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert len(provider.calls) == 2
    # Second attempt includes the first exchange as history.
    assert len(provider.calls[1]["messages"]) == 3


def test_different_system_prompt_is_a_cache_miss(client, provider):
    client.post(
        "/chat",
        json={"session_id": "s-p1", "message": "hello", "system_prompt": "Persona A"},
    )
    response = client.post(
        "/chat",
        json={"session_id": "s-p2", "message": "hello", "system_prompt": "Persona B"},
    )

    assert response.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert len(provider.calls) == 2


def test_simulation_requests_bypass_and_do_not_populate_cache(client, provider):
    payload = {"session_id": "s-sim-cache", "message": "cache bypass check"}
    simulated = client.post(
        "/chat", json=payload, headers={"X-Simulate-Failure": "key_1=429"}
    )
    assert simulated.status_code == 200
    assert simulated.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert simulated.json()["metadata"]["key_id"] == "key_2"

    # A later clean request with the same messages must be a live call, not a hit.
    fresh = client.post("/chat", json={**payload, "session_id": "s-sim-cache-2"})
    assert fresh.status_code == 200
    metadata = fresh.json()["metadata"]
    assert metadata["resolution_source"] == "LIVE_INFERENCE"
    assert metadata["key_id"] == "key_1"
    assert len(provider.calls) == 2
