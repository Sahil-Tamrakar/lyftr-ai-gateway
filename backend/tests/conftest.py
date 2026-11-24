from __future__ import annotations

import json
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
    """Deterministic replacement for ``litellm.acompletion``.

    It emulates LiteLLM's built-in cache: identical ``model`` + ``messages``
    pairs return a copy of the first response marked with
    ``_hidden_params={"cache_hit": True}``.  Requests carrying a ``cache``
    mapping with ``no-cache`` / ``no-store`` bypass both the lookup and the
    write, exactly like LiteLLM's documented bypass flags.
    """

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.upstream_calls: list[dict] = []
        self.reply = "Hello **world**."
        self.input_tokens = 42
        self.output_tokens = 9
        self.failures: dict[str, BaseException] = {}
        self._cache: dict[str, tuple[str, int, int]] = {}

    @staticmethod
    def _cache_key(model: str, messages: list[dict]) -> str:
        return json.dumps(
            {"model": model, "messages": messages},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _response(
        reply: str, input_tokens: int, output_tokens: int, *, cache_hit: bool
    ) -> SimpleNamespace:
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=reply))],
            usage=SimpleNamespace(
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
            ),
            _hidden_params={"cache_hit": cache_hit},
        )

    async def __call__(self, *, model, messages, api_key, timeout, cache=None):
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "api_key": api_key,
                "timeout": timeout,
                "cache": cache,
            }
        )

        bypass = bool(cache and (cache.get("no-cache") or cache.get("no-store")))
        cache_key = self._cache_key(model, messages)

        if not bypass and cache_key in self._cache:
            reply, input_tokens, output_tokens = self._cache[cache_key]
            return self._response(
                reply, input_tokens, output_tokens, cache_hit=True
            )

        failure = self.failures.get(api_key)
        if failure is not None:
            raise failure

        self.upstream_calls.append(
            {"model": model, "messages": messages, "api_key": api_key}
        )
        response = self._response(
            self.reply, self.input_tokens, self.output_tokens, cache_hit=False
        )
        if not bypass:
            self._cache[cache_key] = (self.reply, self.input_tokens, self.output_tokens)
        return response


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
    monkeypatch.setenv("LITELLM_CACHE_TYPE", "local")
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
