# Rehearsed backend — design

FastAPI application providing **versioned REST** (`/api/v1`), **JWT authentication**, **LangGraph**-driven classroom simulation, **PostgreSQL** persistence, and integrations with **Vertex / Gemini**, **Google TTS/STT**, and **Langfuse**.

System context: [../DESIGN.md](../DESIGN.md)  
SPA consumption patterns: [../frontend/DESIGN.md](../frontend/DESIGN.md)

---

## Layered structure

| Layer | Location | Responsibility |
|-------|----------|----------------|
| HTTP / routing | `app/api/v1/*.py` | Routers per domain; validation, auth dependencies, status codes, rate limits. |
| Composition | `app/api/v1/api.py` | Aggregates routers onto `api_router` with prefixes and OpenAPI tags. |
| DI helpers | `app/api/v1/deps.py` | `Depends()` callables for shared singletons (database, TTS). |
| Auth | `app/api/v1/auth.py` | Login, register, session; `get_current_user` / `get_current_session` for protected routes. |
| Domain orchestration | `app/core/langgraph/`, `app/services/` | Graph build/execute, LLM adapters, audio, STT, caches. |
| Data access | `app/services/database/` | `DatabaseService` abstraction over SQLAlchemy / persistence. |
| Config | `app/core/config.py` | Environment-backed `settings` (no Pydantic Settings class—plain loading). |
| Models / schemas | `app/models/`, `app/schemas/` | ORM models vs Pydantic API DTOs—keep boundaries explicit. |

**Pattern — router stays thin:** Parse/validate with Pydantic, authorize with `Depends`, delegate to `DatabaseService` or `LangGraphAgent` (or other services), map exceptions to `HTTPException`.

---

## API composition

`app/main.py` mounts `api_router` at `settings.API_V1_STR` (default `/api/v1`).

| Prefix | Module | Purpose |
|--------|--------|---------|
| `/auth` | `auth.py` | Credentials, JWT, session |
| `/chatbot` | `chatbot.py` | LangGraph chat, streaming where implemented, feedback, STT |
| `/gemini-live` | `gemini_live.py` | Live WebSocket / related endpoints |
| `/scenario` | `scenario.py` | Scenarios and agents for simulation |
| `/admin` | `admin.py` | Global admin CRUD |
| `/user-content` | `user_content.py` | User-scoped content |
| `/tts` | `tts.py` | TTS audio retrieval |
| `/llm-models`, `/llm-config` | `llm_models.py`, `llm_config.py` | Operational LLM configuration |
| `/avatars` | `avatars.py` | Avatar metadata for UI |

OpenAPI: `f"{API_V1_STR}/openapi.json"` as configured on the `FastAPI` app.

---

## Design patterns

### 1. FastAPI dependency injection

- **`get_database_service()`** — Returns process-wide `database_service` singleton.  
- **`get_text_to_speech_service()`** — Returns module-level `GeminiTextToSpeech()` singleton from `deps.py`.  
- **Auth** — `Depends(get_current_session)` or `Depends(get_current_user)` supplies `Session` / `User` after JWT verification.

**Rule:** New shared resources (e.g. a second external client) should get a `get_*` function in `deps.py` rather than importing singletons from random modules.

### 2. Pydantic schemas at the edge

Request and response bodies use `app.schemas.*` types with `response_model=...` where appropriate. ORM models from `app.models` are **not** returned directly unless intentionally compatible—convert in the handler or in a service method.

### 3. Module-level orchestration singletons (intentional tradeoff)

Example: `chatbot.py` holds `agent = LangGraphAgent()` at import time for a single graph coordinator with internal caching (`_graphs` keyed by `scenario_id`).

**Implications:** Tests may patch or reuse this pattern carefully; scaling horizontally requires sticky sessions or externalizing checkpoint/thread state (Postgres checkpointer is supported in the LangGraph stack when enabled).

### 4. LangGraph as the classroom state machine

- **`GraphState`** (`app/schemas/graph.py`) — Single state object: messages, `session_id`, student responses, inline/summary feedback, answering student index, appropriateness flags, learning goals, etc. Reducers (`Annotated[..., add_messages]`, `operator.add`) define merge semantics for parallel updates.  
- **`LangGraphBuilder`** (`app/core/langgraph/graph.py`) — Registers nodes and edges: appropriateness check → pick answering student → parallel **dynamic** student nodes (one per DB agent) → inline feedback → goal check → summary feedback. Uses `RetryPolicy` on nodes for LLM flake.  
- **`LangGraphAgent`** (`app/core/langgraph/graph_entry.py`) — Resolves LLMs (including per-role model names from config), builds/caches compiled graphs per scenario, optional `AsyncPostgresSaver`, wires TTS into nodes that emit audio.

**Pattern:** Scenario-specific behavior flows from **database agent rows**, not from hard-coded graph topology for N students.

### 5. LLM configuration resolution

Model names for different roles (student, answering-student, inline feedback, summary) are resolved through application LLM config services so admins can tune behavior without redeploying code.

### 6. Observability

- **Langfuse** — Initialized in `main.py`; `@observe` on critical paths (e.g. graph creation, checkpointer setup).  
- **Prometheus** — `setup_metrics(app)` and `MetricsMiddleware` for HTTP-level metrics.  
- **Structured logging** — `app.core.logging.logger` with event-style keys (e.g. `chat_request_received`).

### 7. Rate limiting

`slowapi` limiter attached to `app.state.limiter`; per-route limits read from `settings.RATE_LIMIT_ENDPOINTS`. New public or expensive endpoints should get an explicit limit.

### 8. Error handling

- Global handler for `RequestValidationError` returns `422` with flattened field errors for clients.  
- `HTTPException` for domain failures (auth, not found, conflict).  
- Log validation failures with path and client host where available.

### 9. Application lifespan and seed data

`lifespan` context manages startup/shutdown (DB pool, etc., as implemented). Seed functions run on startup in non-`TEST` environments (scenarios → personalities → voices → avatars → agents → feedback → LLM seed data) so local and demo environments have a consistent catalog.

### 10. Caching layers

`feedback_cache`, `tts_audio_cache`, and related helpers avoid redundant LLM or synthesis work where safe. Document TTL and invalidation when adding new caches.

---

## Security patterns

- **JWT** — Secret and algorithm from settings; short-lived access pattern coordinated with frontend session endpoint.  
- **CORS** — `ALLOWED_ORIGINS` from environment; avoid `*` in production when cookies or credentials matter.  
- **Least privilege** — Separate admin routes; verify role or ownership in handlers that mutate content.

---

## Adding a new endpoint (checklist)

1. Define **Pydantic** request/response schemas in `app/schemas/`.  
2. Add handler to the appropriate **`app/api/v1/<domain>.py`** router.  
3. Wire **Depends** for DB, auth, and any feature service.  
4. Apply **`@limiter.limit(...)`** if the route is abuse-prone.  
5. Register router in **`api.py`** if new file.  
6. Extend **OpenAPI** descriptions for client codegen or SPA alignment.  
7. Update **this DESIGN** if you introduce a new cross-cutting pattern (new singleton type, new graph, new integration).

---

## Related files (quick reference)

- App factory: `app/main.py`  
- Router aggregation: `app/api/v1/api.py`  
- Shared DI: `app/api/v1/deps.py`  
- Graph state: `app/schemas/graph.py`  
- Graph builder / entry: `app/core/langgraph/graph.py`, `graph_entry.py`  
- Settings: `app/core/config.py`
