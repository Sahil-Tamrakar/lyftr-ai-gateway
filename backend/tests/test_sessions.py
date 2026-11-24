from __future__ import annotations


def test_session_list_returns_recent_conversations(client, provider):
    client.post(
        "/chat", json={"session_id": "s-list-old", "message": "old question"}
    )
    client.post(
        "/chat",
        json={
            "session_id": "s-list-new",
            "message": "new question",
            "system_prompt": "Be brief.",
        },
    )

    response = client.get("/sessions")
    assert response.status_code == 200

    sessions = response.json()["sessions"]
    ids = [session["session_id"] for session in sessions]
    assert ids.index("s-list-new") < ids.index("s-list-old")

    newest = sessions[ids.index("s-list-new")]
    assert newest["title"] == "new question"
    assert newest["message_count"] == 2
    assert newest["system_prompt"] == "Be brief."

    oldest = sessions[ids.index("s-list-old")]
    assert oldest["title"] == "old question"
    assert oldest["message_count"] == 2
    assert oldest["system_prompt"] is None


def test_session_list_is_empty_without_chats(client):
    response = client.get("/sessions")

    assert response.status_code == 200
    assert response.json() == {"sessions": []}
