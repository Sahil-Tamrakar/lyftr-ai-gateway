"""Pydantic request/response models for the strict HTTP contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator

MESSAGE_MAX_CHARS = 4000
SESSION_ID_MAX_CHARS = 128


class ChatRequest(BaseModel):
    session_id: str
    message: str
    system_prompt: str | None = None

    @field_validator("session_id")
    @classmethod
    def _check_session_id(cls, value: str) -> str:
        if not isinstance(value, str):  # pragma: no cover - pydantic guards type
            raise ValueError("session_id must be a string")
        if not 1 <= len(value) <= SESSION_ID_MAX_CHARS:
            raise ValueError(
                f"session_id must be between 1 and {SESSION_ID_MAX_CHARS} characters"
            )
        return value

    @field_validator("message")
    @classmethod
    def _check_message(cls, value: str) -> str:
        if not isinstance(value, str):  # pragma: no cover - pydantic guards type
            raise ValueError("message must be a string")
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("message must not be empty")
        if len(trimmed) > MESSAGE_MAX_CHARS:
            raise ValueError(
                f"message must be at most {MESSAGE_MAX_CHARS} characters after trimming"
            )
        return trimmed

    @field_validator("system_prompt")
    @classmethod
    def _check_system_prompt(cls, value: str | None) -> str | None:
        # An empty (but explicitly provided) prompt clears the stored one.
        if value is None:
            return None
        return value.strip()


class MessageMetadata(BaseModel):
    resolution_source: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: str | None
    fallback_attempts: int


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    metadata: MessageMetadata


class SessionMessage(BaseModel):
    role: str
    content: str
    metadata: dict[str, Any] | None = None


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: list[SessionMessage]


class SessionSummary(BaseModel):
    session_id: str
    title: str
    updated_at: str
    message_count: int
    system_prompt: str | None = None


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]
