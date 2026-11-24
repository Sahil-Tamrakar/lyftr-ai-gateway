"""Environment-driven application settings.

Everything is read from the process environment (optionally seeded by a
project-root ``.env`` file).  Nothing here ever logs secret key material.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load a local .env when running without Docker (compose injects env directly).
load_dotenv()

_TRUTHY = {"1", "true", "yes", "on"}


def _as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in _TRUTHY


def _as_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _as_csv(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    return tuple(part.strip() for part in raw.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of configuration for one application instance."""

    database_url: str
    llm_api_keys: tuple[str, ...]
    llm_model: str
    allowed_origins: tuple[str, ...]
    enable_failure_simulation: bool
    cache_enabled: bool
    request_timeout: float

    @classmethod
    def from_env(cls) -> "Settings":
        keys = _as_csv("LLM_API_KEYS")
        origins = _as_csv("ALLOWED_ORIGINS") or (
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        )
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:////data/app.db").strip()
            or "sqlite:////data/app.db",
            llm_api_keys=keys,
            llm_model=os.getenv("LLM_MODEL", "gemini/gemini-2.0-flash").strip()
            or "gemini/gemini-2.0-flash",
            allowed_origins=origins,
            enable_failure_simulation=_as_bool("ENABLE_FAILURE_SIMULATION", False),
            cache_enabled=_as_bool("CACHE_ENABLED", True),
            request_timeout=_as_float("LLM_REQUEST_TIMEOUT", 60.0),
        )
