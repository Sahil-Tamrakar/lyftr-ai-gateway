"""LiteLLM gateway: ordered key pool, deterministic cache and failover.

Key routing
-----------
``LLM_API_KEYS`` is parsed into ordered identities ``key_1..key_n``.  Requests
walk the pool sequentially.  A key is only abandoned for *this request* when
LiteLLM raises a rate-limit/quota error or a 5xx-class failure; the pool itself
is never mutated, so a subsequent request starts from ``key_1`` again.

Caching
-------
``litellm.cache`` is enabled for the process, and an application-level cache is
layered in front of it so that a hit is *always* reported deterministically.
The cache key is a SHA-256 over the model name plus the canonical JSON of the
complete message array (system prompt + history + new message), exactly as the
contract requires.  Simulated-failure requests bypass lookup and are never
stored, keeping failover demonstrations stable.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Mapping

from .config import Settings

try:  # pragma: no cover - exercised implicitly by the real deployment
    import litellm
except Exception:  # noqa: BLE001 - LiteLLM is optional for offline unit tests
    litellm = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

#: Status codes that trigger a hand-off to the next key.
FAILOVER_STATUS_CODES = frozenset({408, 409, 429, 500, 502, 503, 504})
#: Status codes accepted by the ``X-Simulate-Failure`` hook.
SIMULATED_STATUS_CODES = frozenset({429, 500, 502, 503})

_KEY_ID_PATTERN = re.compile(r"^key_\d+$")
_MAX_CACHE_ENTRIES = 2048


class AllProvidersUnavailable(RuntimeError):
    """Raised when every key in the pool has been exhausted."""


class ProviderError(RuntimeError):
    """Raised for non-retryable provider failures."""


@dataclass(frozen=True)
class CacheEntry:
    reply: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class GenerationOutcome:
    reply: str
    input_tokens: int
    output_tokens: int
    resolution_source: str
    key_id: str | None
    fallback_attempts: int
    latency_ms: int


# --------------------------------------------------------------------------
# Failure-simulation header
# --------------------------------------------------------------------------
def parse_failure_header(raw: str | None) -> dict[str, int]:
    """Parse ``key_1=429,key_2=500`` / ``*=429`` into a per-request mapping.

    Malformed fragments are ignored rather than failing the request.
    """

    directives: dict[str, int] = {}
    if not raw:
        return directives

    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        target, _, status = chunk.partition("=")
        target = target.strip()
        status = status.strip()
        if target != "*" and not _KEY_ID_PATTERN.match(target):
            continue
        try:
            code = int(status)
        except ValueError:
            continue
        if code in SIMULATED_STATUS_CODES:
            directives[target] = code
    return directives


# --------------------------------------------------------------------------
# Key pool
# --------------------------------------------------------------------------
class KeyPool:
    """Ordered, read-only collection of provider keys."""

    def __init__(self, keys: tuple[str, ...]) -> None:
        self._keys = tuple(keys)

    @property
    def count(self) -> int:
        return len(self._keys)

    def secret_for(self, index: int) -> str:
        return self._keys[index]

    @staticmethod
    def key_id(index: int) -> str:
        return f"key_{index + 1}"


# --------------------------------------------------------------------------
# Deterministic response cache
# --------------------------------------------------------------------------
class ResponseCache:
    def __init__(self, enabled: bool, max_entries: int = _MAX_CACHE_ENTRIES) -> None:
        self.enabled = enabled
        self._max_entries = max_entries
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

    @staticmethod
    def build_key(model: str, messages: list[dict[str, str]]) -> str:
        payload = json.dumps(
            {"model": model, "messages": messages},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def get(self, key: str) -> CacheEntry | None:
        if not self.enabled:
            return None
        async with self._lock:
            entry = self._entries.get(key)
            if entry is not None:
                self._entries.move_to_end(key)
            return entry

    async def set(self, key: str, entry: CacheEntry) -> None:
        if not self.enabled:
            return
        async with self._lock:
            self._entries[key] = entry
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()


# --------------------------------------------------------------------------
# Provider calls
# --------------------------------------------------------------------------
async def _call_provider(
    *, model: str, messages: list[dict[str, str]], api_key: str, timeout: float
) -> Any:
    """Single seam used by every live completion (and by the test suite)."""

    if litellm is None:
        raise ProviderError("litellm is not installed")
    return await litellm.acompletion(
        model=model,
        messages=messages,
        api_key=api_key,
        timeout=timeout,
        drop_params=True,
    )


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


def _as_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_usage(response: Any) -> tuple[int, int]:
    usage = _field(response, "usage")
    input_tokens = _as_int(_field(usage, "prompt_tokens")) or _as_int(
        _field(usage, "input_tokens")
    )
    output_tokens = _as_int(_field(usage, "completion_tokens")) or _as_int(
        _field(usage, "output_tokens")
    )
    return input_tokens or 0, output_tokens or 0


def _extract_reply(response: Any) -> str:
    choices = _field(response, "choices") or []
    if not choices:
        raise ProviderError("provider returned no choices")
    message = _field(choices[0], "message")
    content = _field(message, "content")
    if isinstance(content, list):  # multimodal / content-part responses
        content = "".join(
            str(part.get("text", "")) if isinstance(part, Mapping) else str(part)
            for part in content
        )
    if content is None:
        content = ""
    return str(content).strip()


def _exception_status(exc: BaseException) -> int | None:
    for attribute in ("status_code", "http_status", "status"):
        status = _as_int(getattr(exc, attribute, None))
        if status is not None:
            return status
    response = getattr(exc, "response", None)
    status = _as_int(getattr(response, "status_code", None))
    return status


def _is_failover_error(exc: BaseException) -> bool:
    status = _exception_status(exc)
    if status is not None and status in FAILOVER_STATUS_CODES:
        return True

    if litellm is not None:
        candidates = (
            "RateLimitError",
            "ServiceUnavailableError",
            "InternalServerError",
            "APIConnectionError",
            "Timeout",
            "AuthenticationError",
            "PermissionDeniedError",
        )
        types = tuple(
            candidate
            for candidate in (getattr(litellm, name, None) for name in candidates)
            if isinstance(candidate, type)
        )
        if types and isinstance(exc, types):
            return True

    # Heuristic for provider SDK exceptions that do not expose a status code.
    name = type(exc).__name__.lower()
    markers = (
        "ratelimit",
        "quota",
        "timeout",
        "unavailable",
        "connection",
        "connecterror",
        "internalserver",
        "authentication",
        "permissiondenied",
    )
    return any(marker in name for marker in markers)


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------
class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = settings.llm_model
        self.pool = KeyPool(settings.llm_api_keys)
        self.cache = ResponseCache(enabled=settings.cache_enabled)

    async def complete(
        self,
        messages: list[dict[str, str]],
        simulation: Mapping[str, int] | None = None,
    ) -> GenerationOutcome:
        directives = dict(simulation or {})
        use_cache = not directives
        cache_key = ResponseCache.build_key(self.model, messages)

        if use_cache:
            started = time.perf_counter()
            cached = await self.cache.get(cache_key)
            if cached is not None:
                elapsed = max(0, round((time.perf_counter() - started) * 1000))
                logger.info("Cache hit for model=%s", self.model)
                return GenerationOutcome(
                    reply=cached.reply,
                    input_tokens=cached.input_tokens,
                    output_tokens=cached.output_tokens,
                    resolution_source="LLM_CACHE",
                    key_id=None,
                    fallback_attempts=0,
                    latency_ms=elapsed,
                )

        if self.pool.count == 0:
            logger.warning("No LLM keys configured; cannot serve request")
            raise AllProvidersUnavailable()

        last_error: BaseException | None = None
        for index in range(self.pool.count):
            key_id = self.pool.key_id(index)

            simulated_status = directives.get(key_id) or directives.get("*")
            if simulated_status:
                logger.info("Simulated %s failure for %s (request-scoped)", simulated_status, key_id)
                continue

            attempt_started = time.perf_counter()
            try:
                response = await _call_provider(
                    model=self.model,
                    messages=messages,
                    api_key=self.pool.secret_for(index),
                    timeout=self.settings.request_timeout,
                )
            except Exception as exc:  # noqa: BLE001 - classified below
                if _is_failover_error(exc):
                    logger.warning(
                        "Provider %s failed (%s); failing over", key_id, type(exc).__name__
                    )
                    last_error = exc
                    continue
                logger.error("Provider %s rejected the request (%s)", key_id, type(exc).__name__)
                raise ProviderError("provider request failed") from exc

            latency_ms = max(0, round((time.perf_counter() - attempt_started) * 1000))
            reply = _extract_reply(response)
            input_tokens, output_tokens = _extract_usage(response)

            if use_cache:
                await self.cache.set(
                    cache_key,
                    CacheEntry(
                        reply=reply,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    ),
                )

            return GenerationOutcome(
                reply=reply,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                resolution_source="LIVE_INFERENCE",
                key_id=key_id,
                fallback_attempts=index,
                latency_ms=latency_ms,
            )

        logger.warning("All %d provider keys unavailable", self.pool.count)
        raise AllProvidersUnavailable() from last_error


# --------------------------------------------------------------------------
# LiteLLM built-in cache bootstrap
# --------------------------------------------------------------------------
def configure_litellm_cache(settings: Settings) -> None:
    if litellm is None:
        logger.warning("LiteLLM is not installed; built-in cache unavailable")
        return

    try:
        litellm.suppress_debug_info = True
        logging.getLogger("LiteLLM").setLevel(logging.WARNING)
        if settings.cache_enabled:
            cache_type = os.getenv("LITELLM_CACHE_TYPE", "in-memory").strip() or "in-memory"
            litellm.cache = litellm.Cache(type=cache_type)
            logger.info("LiteLLM cache enabled (type=%s)", cache_type)
        else:
            litellm.cache = None
            logger.info("LiteLLM cache disabled")
    except Exception as exc:  # noqa: BLE001 - never block startup on cache setup
        logger.warning(
            "Could not enable LiteLLM cache (%s); application cache still active",
            type(exc).__name__,
        )
