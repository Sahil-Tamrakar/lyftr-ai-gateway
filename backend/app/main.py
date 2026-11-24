"""FastAPI application exposing the chat contract."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings
from .database import Database
from .llm import (
    AllProvidersUnavailable,
    LLMService,
    ProviderError,
    configure_litellm_cache,
    parse_failure_header,
)
from .schemas import (
    ChatRequest,
    ChatResponse,
    MessageMetadata,
    SessionMessage,
    SessionMessagesResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

router = APIRouter()


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@router.get("/health")
async def health(request: Request) -> JSONResponse:
    db: Database = request.app.state.db
    llm: LLMService = request.app.state.llm
    settings: Settings = request.app.state.settings

    try:
        await db.ping()
    except Exception as exc:  # noqa: BLE001 - reported as unhealthy
        logger.error("Health check failed: database unreachable (%s)", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "keys_configured": llm.pool.count,
                "cache_enabled": settings.cache_enabled,
            },
        )

    return JSONResponse(
        content={
            "status": "ok",
            "keys_configured": llm.pool.count,
            "cache_enabled": settings.cache_enabled,
        }
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    db: Database = request.app.state.db
    llm: LLMService = request.app.state.llm
    settings: Settings = request.app.state.settings

    simulation = None
    if settings.enable_failure_simulation:
        directives = parse_failure_header(request.headers.get("x-simulate-failure"))
        simulation = directives or None

    stored_system_prompt = await db.get_system_prompt(payload.session_id)
    if payload.system_prompt is not None:
        effective_system_prompt = payload.system_prompt or None
        update_system_prompt = True
    else:
        effective_system_prompt = stored_system_prompt
        update_system_prompt = False

    history = await db.get_chat_history(payload.session_id)

    messages: list[dict[str, str]] = []
    if effective_system_prompt:
        messages.append({"role": "system", "content": effective_system_prompt})
    messages.extend({"role": row["role"], "content": row["content"]} for row in history)
    messages.append({"role": "user", "content": payload.message})

    outcome = await llm.complete(messages, simulation)

    metadata = {
        "resolution_source": outcome.resolution_source,
        "model": llm.model,
        "latency_ms": outcome.latency_ms,
        "input_tokens": outcome.input_tokens,
        "output_tokens": outcome.output_tokens,
        "key_id": outcome.key_id,
        "fallback_attempts": outcome.fallback_attempts,
    }

    # Only successful requests are persisted.
    await db.add_exchange(
        session_id=payload.session_id,
        user_content=payload.message,
        assistant_content=outcome.reply,
        assistant_metadata=metadata,
        update_system_prompt=update_system_prompt,
        system_prompt=effective_system_prompt,
    )

    return ChatResponse(
        session_id=payload.session_id,
        reply=outcome.reply,
        metadata=MessageMetadata(**metadata),
    )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=SessionMessagesResponse,
    response_model_exclude_none=True,
)
async def session_messages(session_id: str, request: Request) -> SessionMessagesResponse:
    db: Database = request.app.state.db
    rows = await db.get_chat_history(session_id)

    if not rows:
        return JSONResponse(  # type: ignore[return-value]
            status_code=404, content={"detail": "session not found"}
        )

    messages: list[SessionMessage] = []
    for row in rows:
        if row["role"] == "assistant":
            try:
                metadata = json.loads(row["metadata"]) if row["metadata"] else {}
            except (TypeError, ValueError):
                metadata = {}
            messages.append(
                SessionMessage(role="assistant", content=row["content"], metadata=metadata)
            )
        else:
            messages.append(SessionMessage(role=row["role"], content=row["content"]))

    return SessionMessagesResponse(session_id=session_id, messages=messages)


# --------------------------------------------------------------------------
# Error handlers (always JSON, never HTML or stack traces)
# --------------------------------------------------------------------------
async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "loc": list(error.get("loc", [])),
            "msg": error.get("msg", "invalid value"),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


async def _unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "all providers unavailable"})


async def _provider_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Upstream provider error")
    return JSONResponse(status_code=502, content={"detail": "provider error"})


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled server error (%s)", type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


# --------------------------------------------------------------------------
# Application factory
# --------------------------------------------------------------------------
def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_litellm_cache(resolved_settings)

        db = Database(resolved_settings.database_url)
        await db.connect()
        app.state.db = db
        app.state.llm = LLMService(resolved_settings)
        app.state.settings = resolved_settings

        logger.info(
            "Startup complete: model=%s keys=%d simulation=%s cache=%s",
            resolved_settings.llm_model,
            len(resolved_settings.llm_api_keys),
            resolved_settings.enable_failure_simulation,
            resolved_settings.cache_enabled,
        )
        try:
            yield
        finally:
            await db.close()

    app = FastAPI(
        title="LLM Chat Gateway",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )

    origins = list(resolved_settings.allowed_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(AllProvidersUnavailable, _unavailable_handler)
    app.add_exception_handler(ProviderError, _provider_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)

    app.include_router(router)
    return app


app = create_app()
