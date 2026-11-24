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
    assert len(provider.upstream_calls) == 1
    assert provider.calls[0]["cache"] is None

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

    # LiteLLM was invoked again, but no additional upstream call was made.
    assert len(provider.calls) == 2
    assert len(provider.upstream_calls) == 1


def test_same_session_repeat_is_a_miss_because_history_changed(client, provider):
    payload = {"session_id": "s-cache-history", "message": "hello"}
    first = client.post("/chat", json=payload)
    second = client.post("/chat", json=payload)

    assert first.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert second.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert len(provider.upstream_calls) == 2
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
    assert len(provider.upstream_calls) == 2


def test_simulation_requests_bypass_and_do_not_populate_cache(client, provider):
    payload = {"session_id": "s-sim-cache", "message": "cache bypass check"}
    simulated = client.post(
        "/chat", json=payload, headers={"X-Simulate-Failure": "key_1=429"}
    )
    assert simulated.status_code == 200
    assert simulated.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert simulated.json()["metadata"]["key_id"] == "key_2"
    assert simulated.json()["metadata"]["fallback_attempts"] == 1

    # LiteLLM receives the documented bypass flags for simulated requests.
    assert provider.calls[0]["cache"] == {"no-cache": True, "no-store": True}
    assert len(provider.upstream_calls) == 1

    # A later clean request with the same messages must be a live call, not a hit.
    fresh = client.post("/chat", json={**payload, "session_id": "s-sim-cache-2"})
    assert fresh.status_code == 200
    metadata = fresh.json()["metadata"]
    assert metadata["resolution_source"] == "LIVE_INFERENCE"
    assert metadata["key_id"] == "key_1"
    assert len(provider.upstream_calls) == 2


def test_simulation_does_not_read_an_existing_cache_entry(client, provider):
    payload = {"session_id": "s-cached-before", "message": "read from cache?"}
    primed = client.post("/chat", json=payload)
    assert primed.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert len(provider.upstream_calls) == 1

    simulated = client.post(
        "/chat",
        json={**payload, "session_id": "s-cached-before-2"},
        headers={"X-Simulate-Failure": "key_1=429"},
    )

    metadata = simulated.json()["metadata"]
    assert metadata["resolution_source"] == "LIVE_INFERENCE"
    assert metadata["key_id"] == "key_2"
    assert metadata["fallback_attempts"] == 1
    assert provider.calls[-1]["cache"] == {"no-cache": True, "no-store": True}
    assert len(provider.upstream_calls) == 2


def test_litellm_builtin_cache_is_configured_at_startup(client):
    import litellm

    assert litellm.cache is not None
    assert getattr(litellm.cache, "type", None) == "local"
