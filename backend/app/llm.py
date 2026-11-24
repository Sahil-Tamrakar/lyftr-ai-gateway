"""LiteLLM gateway: ordered key pool, built-in cache and failover.

Key routing
-----------
``LLM_API_KEYS`` is parsed into ordered identities ``key_1..key_n``.  Requests
walk the pool sequentially.  A key is only abandoned for *this request* when
LiteLLM raises a rate-limit/quota error or a 5xx-class failure; the pool itself
is never mutated, so a subsequent request starts from ``key_1`` again.

Caching
-------
Caching is delegated entirely to LiteLLM.  ``litellm.cache`` is configured at
startup with LiteLLM's built-in ``Cache`` (in-memory by default, or any backend
supported by the installed LiteLLM build via ``LITELLM_CACHE_TYPE``).  LiteLLM
derives its own deterministic cache key from the model and the complete message
array, so identical requests across sessions resolve to the same entry.

A cache hit is detected from LiteLLM's response metadata:

    response._hidden_params["cache_hit"] is True

Requests carrying ``X-Simulate-Failure`` pass ``{"no-cache": True,
"no-store": True}`` to LiteLLM so simulated requests neither read an existing
entry nor pollute the cache, keeping failover demonstrations reproducible.
"""

from __future__ import annotations

import logging
import os
import re
import time
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

#: Instructs LiteLLM to bypass both cache lookup and cache writes.
CACHE_BYPASS = {"no-cache": True, "no-store": True}

_KEY_ID_PATTERN = re.compile(r"^key_\d+$")


class AllProvidersUnavailable(RuntimeError):
    """Raised when every key in the pool has been exhausted."""


class ProviderError(RuntimeError):
    """Raised for non-retryable provider failures."""


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
# Provider calls
# --------------------------------------------------------------------------
async def _call_provider(
    *,
    model: str,
    messages: list[dict[str, str]],
    api_key: str,
    timeout: float,
    cache: Mapping[str, bool] | None = None,
) -> Any:
    """Single seam used by every live completion (and by the test suite).

    ``cache`` is forwarded to LiteLLM verbatim; when it carries ``no-cache`` /
    ``no-store`` LiteLLM skips both the cache read and the cache write.
    """

    if litellm is None:
        raise ProviderError("litellm is not installed")

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "api_key": api_key,
        "timeout": timeout,
        "drop_params": True,
    }
    if cache:
        kwargs["cache"] = dict(cache)

    return await litellm.acompletion(**kwargs)


def _field(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


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


def _is_cache_hit(response: Any) -> bool:
    """Read LiteLLM's built-in cache-hit flag from the response metadata."""

    hidden = _field(response, "_hidden_params", {}) or {}
    return bool(_field(hidden, "cache_hit", False))


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

    async def complete(
        self,
        messages: list[dict[str, str]],
        simulation: Mapping[str, int] | None = None,
    ) -> GenerationOutcome:
        directives = dict(simulation or {})
        cache_kwargs: Mapping[str, bool] | None = CACHE_BYPASS if directives else None

        if self.pool.count == 0:
            logger.warning("No LLM keys configured; cannot serve request")
            raise AllProvidersUnavailable()

        last_error: BaseException | None = None
        for index in range(self.pool.count):
            key_id = self.pool.key_id(index)

            simulated_status = directives.get(key_id) or directives.get("*")
            if simulated_status:
                logger.info(
                    "Simulated %s failure for %s (request-scoped)",
                    simulated_status,
                    key_id,
                )
                continue

            attempt_started = time.perf_counter()
            try:
                response = await _call_provider(
                    model=self.model,
                    messages=messages,
                    api_key=self.pool.secret_for(index),
                    timeout=self.settings.request_timeout,
                    cache=cache_kwargs,
                )
            except Exception as exc:  # noqa: BLE001 - classified below
                if _is_failover_error(exc):
                    logger.warning(
                        "Provider %s failed (%s); failing over",
                        key_id,
                        type(exc).__name__,
                    )
                    last_error = exc
                    continue
                logger.error(
                    "Provider %s rejected the request (%s)",
                    key_id,
                    type(exc).__name__,
                )
                raise ProviderError("provider request failed") from exc

            latency_ms = max(0, round((time.perf_counter() - attempt_started) * 1000))
            reply = _extract_reply(response)
            input_tokens, output_tokens = _extract_usage(response)

            if _is_cache_hit(response):
                logger.info("LiteLLM cache hit for model=%s", self.model)
                return GenerationOutcome(
                    reply=reply,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    resolution_source="LLM_CACHE",
                    key_id=None,
                    fallback_attempts=0,
                    latency_ms=latency_ms,
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
    """Attach LiteLLM's built-in cache to the process."""

    if litellm is None:
        logger.warning("LiteLLM is not installed; built-in cache unavailable")
        return

    try:
        litellm.suppress_debug_info = True
        logging.getLogger("LiteLLM").setLevel(logging.WARNING)
        if settings.cache_enabled:
            cache_type = os.getenv("LITELLM_CACHE_TYPE", "local").strip() or "local"
            try:
                litellm.cache = litellm.Cache(type=cache_type)
            except Exception as exc:  # noqa: BLE001 - fall back to in-memory cache
                logger.warning(
                    "Unsupported LITELLM_CACHE_TYPE=%s (%s); falling back to local",
                    cache_type,
                    type(exc).__name__,
                )
                cache_type = "local"
                litellm.cache = litellm.Cache(type=cache_type)
            logger.info("LiteLLM cache enabled (type=%s)", cache_type)
        else:
            litellm.cache = None
            logger.info("LiteLLM cache disabled")
    except Exception as exc:  # noqa: BLE001 - never block startup on cache setup
        logger.warning(
            "Could not enable LiteLLM cache (%s); requests will run uncached",
            type(exc).__name__,
        )
