from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.llm as llm_module
from app.config import Settings
from app.main import create_app


class ProviderHTTPError(Exception):
    """Stand-in for a LiteLLM error that carries an HTTP status code."""

    def __init__(self, status_code: int, message: str = "provider error") -> None:
        super().__init__(message)
        self.status_code = status_code


class FakeProvider:
    """Deterministic replacement for ``litellm.acompletion``."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.reply = "Hello **world**."
        self.input_tokens = 42
        self.output_tokens = 9
        self.failures: dict[str, BaseException] = {}

    async def __call__(self, *, model, messages, api_key, timeout):
        self.calls.append(
            {"model": model, "messages": messages, "api_key": api_key, "timeout": timeout}
        )
        failure = self.failures.get(api_key)
        if failure is not None:
            raise failure
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply))],
            usage=SimpleNamespace(
                prompt_tokens=self.input_tokens,
                completion_tokens=self.output_tokens,
            ),
        )


@pytest.fixture
def provider(monkeypatch) -> FakeProvider:
    fake = FakeProvider()
    monkeypatch.setattr(llm_module, "_call_provider", fake)
    return fake


def make_client(
    tmp_path,
    monkeypatch,
    *,
    simulation: bool = True,
    keys: str = "test-key-one,test-key-two",
    model: str = "gemini/gemini-2.0-flash",
) -> TestClient:
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("LLM_API_KEYS", keys)
    monkeypatch.setenv("LLM_MODEL", model)
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000")
    monkeypatch.setenv("ENABLE_FAILURE_SIMULATION", "true" if simulation else "false")
    monkeypatch.setenv("CACHE_ENABLED", "true")
    monkeypatch.setenv("LLM_REQUEST_TIMEOUT", "5")

    application = create_app(Settings.from_env())
    return TestClient(application)


@pytest.fixture
def client(tmp_path, monkeypatch, provider) -> TestClient:
    with make_client(tmp_path, monkeypatch) as test_client:
        yield test_client


@pytest.fixture
def client_no_simulation(tmp_path, monkeypatch, provider) -> TestClient:
    with make_client(tmp_path, monkeypatch, simulation=False) as test_client:
        yield test_client
