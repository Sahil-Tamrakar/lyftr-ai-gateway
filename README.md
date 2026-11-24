# LLM Chatbot with Key Failover & Response Caching

A production-shaped LLM gateway and observability console.

- **Backend** — FastAPI + LiteLLM + `aiosqlite`, with an ordered key pool,
  request-scoped failover, deterministic response caching, per-request token
  accounting and strict JSON error envelopes.
- **Frontend** — React + Vite + TypeScript + Tailwind console that renders
  markdown with syntax highlighting and surfaces routing metadata for every
  assistant reply.
- **Infrastructure** — multi-stage Dockerfiles, Docker Compose with a named
  SQLite volume, and a Makefile.

```
.
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, lifespan, endpoints, error handlers
│   │   ├── config.py        # environment settings
│   │   ├── database.py      # async SQLite storage
│   │   ├── schemas.py       # request/response models + validation
│   │   └── llm.py           # key pool, cache, failover, simulation hook
│   ├── tests/               # pytest suite (no live provider required)
│   ├── Dockerfile           # wheel builder -> slim non-root runtime
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api.ts
│   │   └── components/
│   ├── Dockerfile           # node builder -> nginx runtime, port 3000
│   └── nginx.conf
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

## 1. Live URLS

The compose stack serves the application at:

| Surface | URL |
| --- | --- |
| Console UI | http://localhost:3000 |
| API | http://localhost:8000 |
| Health | http://localhost:8000/health |
| OpenAPI docs | http://localhost:8000/docs |

No public deployment is bundled with this repository. To publish it, deploy the
two images and set `VITE_API_BASE_URL` to the public backend URL at frontend
build time (and add the frontend origin to `ALLOWED_ORIGINS`).

## 2. Run locally: with Docker and without

### With Docker (recommended)

```bash
cp .env.example .env
# put your real, comma-separated keys in LLM_API_KEYS
make up
```

Then open http://localhost:3000. SQLite lives on the named volume
`llm-gateway_app-data`, mounted at `/data`, so conversations survive
`make down` / `make up`.

```bash
make down      # stop the stack (data is preserved)
make logs      # follow both services
```

### Without Docker

Backend (Python 3.11+):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

export DATABASE_URL=sqlite:///./app.db
export LLM_API_KEYS=key-one,key-two,key-three
export LLM_MODEL=gemini/gemini-2.0-flash
export ALLOWED_ORIGINS=http://localhost:3000
export ENABLE_FAILURE_SIMULATION=true

uvicorn app.main:app --reload --port 8000
```

Frontend (Node 20+):

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

Run the backend test suite (no API keys or network required — the provider
call is stubbed):

```bash
cd backend
python -m pytest -q
```

## 3. Design decisions: key fallback, caching, SQLite session storage

### Key fallback

- `LLM_API_KEYS` is split into ordered identities `key_1`, `key_2`, `key_3`, …
  Only the identity is ever reported or logged; raw keys stay inside the
  process and are passed to LiteLLM per attempt.
- Each request walks the pool sequentially. A key is abandoned for that request
  on HTTP `429`, quota/rate-limit errors, timeouts, connection failures,
  authentication/permission errors and any `5xx`. There is no shared mutable
  "failed key" state, so a key that failed once is retried on the next request.
- `fallback_attempts` is the zero-based index of the key that served the
  request: `0` when `key_1` succeeds, `1` when `key_2` does, and so on.
  `key_id` names the serving identity. If every key fails, the API returns
  `503` with exactly `{"detail": "all providers unavailable"}`.
- `X-Simulate-Failure` (only when `ENABLE_FAILURE_SIMULATION=true`) accepts
  `key_1=429`, `key_1=429,key_2=500`, or `*=429`; supported codes are `429`,
  `500`, `502`, `503`. Simulated failures are evaluated before any network
  call, apply only to the current request, and are capped at the key they name.

### Caching

- LiteLLM's built-in cache is enabled at startup (`litellm.cache = Cache(...)`),
  with `LITELLM_CACHE_TYPE=in-memory` by default.
- Layered in front of it is a deterministic, bounded LRU cache owned by the
  gateway so a hit can always be reported precisely. Its key is
  `sha256(model + canonical-JSON(full message array))`, where the message array
  is the effective system prompt + persisted history + the new user message.
- A hit returns the stored reply, the stored `input_tokens` / `output_tokens`,
  `resolution_source: "LLM_CACHE"`, `key_id: null`, `fallback_attempts: 0`, and
  does not call a provider.
- Because history is part of the key, repeating the same prompt in the *same*
  session is intentionally a miss (the history changed). Cache hits are
  demonstrated with a fresh `session_id` and an identical prompt.
- Requests carrying `X-Simulate-Failure` bypass the cache lookup **and** are
  never written to the cache. That keeps failover demos reproducible: a clean
  request after a simulated one still hits `key_1` live.

### SQLite session storage

- `DATABASE_URL` defaults to `sqlite:////data/app.db`. The parent directory is
  created automatically and tables/indexes are initialized during FastAPI
  `lifespan`.
- The exact contract schema is used (`messages` with
  `id, session_id, role, content, metadata, created_at`) plus an index on
  `(session_id, id)`. WAL mode and a busy timeout keep concurrent reads/writes
  healthy.
- A system prompt is stored as a hidden `role='system'` row and excluded from
  the public message listing. An explicitly empty `system_prompt` clears it.
- A successful turn writes the user message and assistant message in one
  transaction, including the routing metadata JSON. Validation failures (`422`)
  and provider exhaustion (`503`) never touch the database.
- Tokens come from the provider's usage for that single call
  (prompt + history + new message → reply), never from a cumulative counter.

## 4. Verification: how to see failover, cache hits and per-message token usage

All examples assume the compose stack on `http://localhost:8000` with two or
more keys configured.

**Health**

```bash
curl -s http://localhost:8000/health
# {"status":"ok","keys_configured":3,"cache_enabled":true}
```

**Live inference**

```bash
curl -s -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"s-demo","message":"Explain failover in one sentence."}'
```

`metadata.resolution_source` is `LIVE_INFERENCE`, `key_id` is `"key_1"`,
`fallback_attempts` is `0`, and `input_tokens` / `output_tokens` describe only
this turn.

**Failover (key_1 fails for this request only)**

```bash
curl -s -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Simulate-Failure: key_1=429' \
  -d '{"session_id":"s-failover","message":"Which key served me?"}'
```

Response metadata:

```json
{
  "resolution_source": "LIVE_INFERENCE",
  "key_id": "key_2",
  "fallback_attempts": 1
}
```

Send the same request again without the header (fresh session) and `key_id`
returns to `key_1` — the pool was not poisoned.

**All keys unavailable**

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Simulate-Failure: *=429' \
  -d '{"session_id":"s-outage","message":"nobody home"}'
# 503
```

`GET /sessions/s-outage/messages` then returns `404`; nothing was persisted.

**Cache hit** (identical prompt, fresh session, no simulation header)

```bash
curl -s -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"s-cache-1","message":"What is 2 + 2?"}'

curl -s -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"s-cache-2","message":"What is 2 + 2?"}'
```

The second response has `resolution_source: "LLM_CACHE"`, `key_id: null`,
`fallback_attempts: 0`, and the same token counts as the first.

**History**

```bash
curl -s http://localhost:8000/sessions/s-demo/messages
# role/content oldest-first, assistant entries include metadata, no system prompt
```

**In the UI**

- `chat-input`, `send-button` and `system-prompt-input` drive the session; the
  input clears immediately on send, Enter sends, Shift+Enter inserts a newline.
- Each assistant card is `assistant-message` and contains
  `meta-source` (`LIVE_INFERENCE` / `LLM_CACHE`), `meta-model`,
  `meta-latency` (`812 ms`), `meta-input-tokens`, `meta-output-tokens`, plus
  `meta-key-id` and a fallback badge when routing skipped keys.
- Validation and outage failures appear as readable red alert bubbles inside
  the stream (HTTP status included), not as console errors.

## 5. Setup Used: your editor and AI tools

- Editor/tooling: VS Code-style workspace driven by **Codebuff** (Buffy running
  on DeepSeek V4.1 Flash Slow).
- Verification environment: Python 3.12.1, Node 24.18.0 / npm 12.2.3 on
  Windows. `pytest` (23 tests) and the production frontend build (`tsc` +
  `vite build`) were executed locally.
- Docker was not installed on the authoring machine, so `docker compose up`
  was not executed here; the Dockerfiles, compose file and Makefile are
  provided and written for the documented ports/volumes.

## 6. Bonus features (if any): what you added beyond the requirements and why

- **Cache-bypass invariant for simulations** — simulated requests neither read
  nor write the cache, which guarantees a failover demo cannot accidentally
  turn into a cache hit and makes tests deterministic.
- **Bounded LRU response cache** (2048 entries) — prevents unbounded memory
  growth in a long-running process while keeping hit semantics exact.
- **Extra routing telemetry in the UI** — `meta-key-id` and a `fallback ×N`
  badge make the key pool observable, not just the resolution source.
- **Copy affordances** — copy reply and copy session id buttons for quick
  report/demo pasting.
- **Health-aware header** — polls `/health` and shows API state, key count and
  cache state at a glance.
- **Hardened error surface** — custom handlers guarantee JSON `detail`
  envelopes for all failures (no HTML pages or stack traces), and the backend
  container runs as a non-root user.
- **Provider-side failover tests** — beyond simulated headers, tests inject
  real `429`/`5xx` provider exceptions to verify classification and exhaustion.
- **Container healthchecks** for both services, and immutable asset caching in
  Nginx.
