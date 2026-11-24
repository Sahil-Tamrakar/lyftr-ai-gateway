from __future__ import annotations

METADATA_KEYS = {
    "resolution_source",
    "model",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "key_id",
    "fallback_attempts",
}


def test_chat_success_shape_and_metadata(client, provider):
    response = client.post("/chat", json={"session_id": "s-abc", "message": "Hi"})

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "s-abc"
    assert body["reply"] == provider.reply
    metadata = body["metadata"]
    assert set(metadata) == METADATA_KEYS
    assert metadata["resolution_source"] == "LIVE_INFERENCE"
    assert metadata["model"] == "gemini/gemini-2.0-flash"
    assert metadata["input_tokens"] == 42
    assert metadata["output_tokens"] == 9
    assert metadata["key_id"] == "key_1"
    assert metadata["fallback_attempts"] == 0
    assert isinstance(metadata["latency_ms"], int)
    assert metadata["latency_ms"] >= 0


def test_multi_turn_persists_ordered_history_without_system_prompt(client, provider):
    first = client.post(
        "/chat",
        json={"session_id": "s-multi", "message": "first", "system_prompt": "Be terse."},
    )
    assert first.status_code == 200

    second = client.post(
        "/chat", json={"session_id": "s-multi", "message": "second"}
    )
    assert second.status_code == 200

    # Second call replays the stored system prompt + both prior turns.
    sent = provider.calls[1]["messages"]
    assert sent[0] == {"role": "system", "content": "Be terse."}
    assert sent[1:] == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": provider.reply},
        {"role": "user", "content": "second"},
    ]

    history = client.get("/sessions/s-multi/messages")
    assert history.status_code == 200
    data = history.json()
    assert data["session_id"] == "s-multi"
    assert [message["role"] for message in data["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert data["messages"][0] == {"role": "user", "content": "first"}
    assert "metadata" not in data["messages"][0]
    assistant = data["messages"][1]
    assert assistant["content"] == provider.reply
    assert assistant["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert assistant["metadata"]["input_tokens"] == 42
    assert assistant["metadata"]["key_id"] == "key_1"


def test_tokens_are_per_request_not_cumulative(client, provider):
    client.post("/chat", json={"session_id": "s-tokens", "message": "one"})
    provider.input_tokens = 7
    provider.output_tokens = 3

    response = client.post("/chat", json={"session_id": "s-tokens", "message": "two"})
    metadata = response.json()["metadata"]

    assert metadata["input_tokens"] == 7
    assert metadata["output_tokens"] == 3


def test_system_prompt_persists_and_can_be_cleared(client, provider):
    client.post(
        "/chat",
        json={"session_id": "s-sys", "message": "hello", "system_prompt": "ROLE: analyst"},
    )
    client.post("/chat", json={"session_id": "s-sys", "message": "again"})
    assert provider.calls[1]["messages"][0] == {
        "role": "system",
        "content": "ROLE: analyst",
    }

    # An explicitly empty system prompt clears the stored persona.
    client.post(
        "/chat",
        json={"session_id": "s-sys", "message": "reset", "system_prompt": ""},
    )
    assert provider.calls[2]["messages"][0] == {"role": "user", "content": "hello"}

    client.post("/chat", json={"session_id": "s-sys", "message": "after clear"})
    assert all(
        message["role"] != "system" for message in provider.calls[3]["messages"]
    )

    history = client.get("/sessions/s-sys/messages").json()
    assert all(message["role"] != "system" for message in history["messages"])


def test_message_is_trimmed_before_send_and_store(client, provider):
    response = client.post(
        "/chat", json={"session_id": "s-trim", "message": "   padded   "}
    )

    assert response.status_code == 200
    assert provider.calls[0]["messages"][-1] == {"role": "user", "content": "padded"}
    history = client.get("/sessions/s-trim/messages").json()
    assert history["messages"][0]["content"] == "padded"


def test_message_boundary_of_4000_chars_is_accepted(client):
    response = client.post(
        "/chat", json={"session_id": "s-limit", "message": "a" * 4000}
    )
    assert response.status_code == 200


def test_validation_errors_return_422_and_do_not_touch_db(client):
    cases = [
        {"session_id": "s-bad", "message": ""},
        {"session_id": "s-bad", "message": "    "},
        {"session_id": "s-bad", "message": "a" * 4001},
        {"session_id": "", "message": "hello"},
        {"session_id": "x" * 129, "message": "hello"},
        {"session_id": "s-bad"},
        {"message": "hello"},
    ]

    for payload in cases:
        response = client.post("/chat", json=payload)
        assert response.status_code == 422, payload
        body = response.json()
        assert "detail" in body
        assert isinstance(body["detail"], list)

    assert client.get("/sessions/s-bad/messages").status_code == 404


def test_unknown_session_returns_exact_404(client):
    response = client.get("/sessions/does-not-exist/messages")

    assert response.status_code == 404
    assert response.json() == {"detail": "session not found"}
