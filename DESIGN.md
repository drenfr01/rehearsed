# Rehearsed — system design

Rehearsed is a **teacher simulation platform**: educators practice in AI-driven classroom scenarios and receive structured feedback on their teaching. A teacher selects a scenario (e.g. a specific classroom situation with defined teaching objectives), interacts with AI-simulated students, and receives both **inline feedback** during the session and a **summary feedback** report when the scenario's learning goals are achieved.

This document is the **system-level** view. Implementation patterns and conventions live in:

- [frontend/DESIGN.md](frontend/DESIGN.md) — Angular SPA structure, routing, HTTP, and UI patterns
- [backend/DESIGN.md](backend/DESIGN.md) — FastAPI layering, LangGraph, persistence, and API patterns
- [docs/auth-redesign.md](docs/auth-redesign.md) — JWT hardening: typed tokens, secret validation, admin-claim changes

---

## Product overview

### Simulation modes

| Mode | Experience | Backend path |
|------|------------|--------------|
| **Multi-student classroom** | Teacher addresses a simulated class; a student is chosen to respond each turn, with optional TTS audio playback and STT voice input | LangGraph graph compiled per scenario, driven by `POST /api/v1/chatbot/chat` |
| **One-on-one voice** | Real-time spoken conversation with a single student agent | Gemini Live proxied over `WS /api/v1/gemini-live/ws`, with post-session summary via `POST /api/v1/gemini-live/summary-feedback` |

### Feedback

- **Inline feedback** — generated in parallel with each student response and fetched asynchronously by the client (`GET /api/v1/chatbot/feedback/{id}`).
- **Summary feedback** — generated when the graph determines the scenario's teaching goals are achieved (classroom mode), or on demand after a one-on-one session.
- Feedback definitions (objective, instructions, constraints, output format) are **data**, stored per scenario with `feedback_type` of `inline` or `summary`.

### Content model

All simulation content is configurable, not hard-coded:

- **Scenarios** — name, description, overview, system instructions, initial prompt, teaching objectives.
- **Agents (students)** — belong to a scenario; carry objective/instructions/constraints/context, a personality, a voice, an avatar, and a display color.
- **Personalities, voices, avatars** — reusable building blocks for agents.
- **Feedback definitions** — per-scenario inline and summary prompts.
- **LLM config** — which Gemini model each agent type uses (`student_agent`, `student_choice_agent`, `inline_feedback`, `summary_feedback`), editable by admins at runtime.

**Ownership pattern:** every content row has an `owner_id`. `NULL` means global (admin-managed catalog, seeded at startup from YAML in `backend/app/seed_data/`); a user id means user-local content. Users can copy global content into their own space and customize it via the **My Content** UI; admins manage the global catalog via the **Admin** UI.

### Users and access

- Registration creates an unapproved account (`is_approved=False`); an admin must approve it before login succeeds.
- `is_admin` gates the admin route tree (backend dependency check) and the admin UI (JWT claim).

---

## Architecture overview

| Layer | Technology | Responsibility |
|--------|------------|----------------|
| Client | Angular 20 + Material (standalone components, signals) | Auth, scenario flows, classroom / 1:1 UI, admin and user-content CRUD, WebSocket client for Gemini Live |
| API | FastAPI (Python 3.13, SQLModel) | REST under `/api/v1`, JWT auth, rate limits (slowapi), CORS, Prometheus metrics |
| Orchestration | LangGraph + LangChain (Vertex AI / Gemini) | Per-scenario conversation graph: appropriateness check, student agents, inline/summary feedback |
| Data | PostgreSQL (Cloud SQL in prod) | Users, sessions, scenarios, agents, personalities, voices, avatars, feedback definitions, LLM config; LangGraph checkpoints via `AsyncPostgresSaver` |
| Speech | Google Cloud TTS / STT + Gemini Live | Student audio playback, voice input, live voice conversation |
| Observability | Langfuse + Prometheus/Grafana | LLM traces, request metrics |
| Hosting | Cloud Run (backend) + Firebase Hosting (frontend) | Deployment targets (see README) |

---

## API surface (all under `/api/v1`)

| Prefix | Purpose |
|--------|---------|
| `/auth` | Register, login, session create/rename/delete/list |
| `/chatbot` | Classroom chat (`/chat`, `/chat/stream`), message history, inline feedback retrieval |
| `/gemini-live` | One-on-one WebSocket (`/ws`) and summary feedback |
| `/scenario` | List scenarios (global + user-local), get by id, set current, list per-scenario agents |
| `/admin` | Global catalog CRUD + user approval (admin session required) |
| `/user-content` | User-scoped CRUD and copy-from-global for scenarios, agents, personalities, feedback |
| `/tts` | Lazy audio retrieval by `audio_id` |
| `/llm-models`, `/llm-config` | Model catalog and per-agent-type model assignment (admin) |
| `/avatars` | Avatar catalog (public) |

OpenAPI is served at `{API_V1_STR}/openapi.json`; Swagger UI at `/docs`.

---

## Major data flows

1. **Teacher session (LangGraph / chatbot)**
   The teacher selects a scenario via authenticated `POST /api/v1/scenario/set-current-by-id`, which persists `scenario_id` on the session row (access-checked: global scenarios or the user's own). Authenticated `POST /api/v1/chatbot/chat` then drives a compiled graph for the session's scenario. The graph (built by `LangGraphBuilder`, cached per scenario by the `LangGraphAgent` singleton) flows:

   ```
   START → check_appropriate_response
         ├─ inappropriate → gather_new_human_response → (loop)
         └─ appropriate   → pick_answering_student
                            ├─ student_{N}_agent      (one node per DB agent, runs chosen student)
                            └─ inline_feedback_agent  (parallel)
                            → additional_user_input → check_if_goals_achieved
                              ├─ not yet  → loop to appropriateness check
                              └─ achieved → generate_summary_feedback → END
   ```

   State (`GraphState`) tracks messages, student responses, inline/summary feedback, the answering student, appropriateness, and goal flags. Conversation state is checkpointed to Postgres (`AsyncPostgresSaver`) keyed by session. Student responses may be voiced: TTS audio is generated and exposed lazily via `GET /api/v1/tts/{audio_id}`.

2. **Live voice (Gemini Live)**
   The SPA opens `WS /api/v1/gemini-live/ws?token={session_jwt}`. The backend builds the system prompt from scenario + agent data and proxies bidirectional audio/text to the Gemini Live API. Message types: client sends `setup`/`audio`/`text`/`end`; server returns `setup_complete`, `audio`, `transcript_user`, `transcript_agent`, `turn_complete`, `error`. Summary feedback is requested over HTTP afterward.

3. **Content management**
   **Admin** routes manage the global catalog (owner_id = NULL). **User content** routes manage user-scoped copies and originals. **Scenario** routes expose selection and per-scenario agents for the active simulation. Global content is seeded idempotently at startup from YAML (`scenario_data.yaml`, `agent_data.yaml`, `feedback_data_*.yaml`, plus personality/voice/avatar/LLM seed modules).

---

## Cross-cutting concerns

- **Authentication:** Two typed JWTs (`python-jose`): a short-lived **user token** (~15 min) from `/auth/login`, exchanged at `/auth/session` for a long-lived **session token** (~7 days) tied to a session row. `verify_token` enforces the expected type per endpoint. The Gemini Live WebSocket authenticates via a `token` query param.
- **Authorization:** Separate route trees for admin vs user content; handlers use `Depends(get_current_session)`, `get_current_user`, or `get_current_admin_user` as appropriate. Content access checks compare `owner_id` against the requesting user.
- **Configuration:** Environment-driven settings in `app/core/config.py` (CORS, per-endpoint rate limits, JWT secrets — ≥32 chars enforced outside tests — model names, GCP project/location, Langfuse keys). LLM-per-agent-type assignment lives in the `agent_llm_config` table and is hot-swappable via `/llm-config` (cache invalidated on update).
- **Resilience:** LangGraph node `RetryPolicy` for transient LLM failures; rate limiting on hot endpoints; `/health` performs a DB connectivity check.
- **Observability:** Langfuse traces on LLM-heavy paths; Prometheus metrics middleware with Grafana dashboards (`backend/prometheus/`, `backend/grafana/`).

---

## Repository layout

```
rehearsed/
├── frontend/                # Angular 20 SPA — see frontend/DESIGN.md
│   ├── src/app/core/        # Services (Auth, Scenario, ChatGraph, GeminiLive, Admin, UserContent), guards, interceptors, models
│   ├── src/app/features/    # Login/register, scenario selection/overview, classroom, one-on-one, my-content, admin
│   └── firebase.json        # Firebase Hosting config
├── backend/                 # FastAPI + LangGraph — see backend/DESIGN.md
│   ├── app/api/v1/          # Routers: auth, chatbot, gemini_live, scenario, admin, user_content, tts, llm_*, avatars
│   ├── app/core/            # config, langgraph (graph builder, entry, tools), llm factory, prompts, limiter, logging
│   ├── app/models/          # SQLModel tables
│   ├── app/schemas/         # Pydantic request/response + GraphState
│   ├── app/services/        # database repositories, TTS/STT, gemini_live, feedback/tts caches, summary feedback
│   ├── app/seed_data/       # YAML + seeders for global catalog
│   ├── tests/               # unit / integration / e2e
│   └── evals/               # LLM evaluation harness
├── docs/                    # auth redesign, LLM model improvement notes
└── DESIGN.md                # This file
```

---

## Design principles (product + engineering)

1. **Scenario-centric simulation** — The graph and agent roster are built from the selected scenario's data in the database, not hard-coded student count.
2. **Content as data** — Scenarios, agents, personalities, feedback prompts, and model assignments are all DB rows editable through the UI; code defines behavior, data defines content.
3. **API-first** — The SPA is a client of versioned REST; contracts should stay aligned with OpenAPI and shared schema names where possible.
4. **Observable AI** — LLM-heavy paths are instrumented (e.g. Langfuse) so regressions and cost can be traced per environment.
5. **Thin transport, rich domain** — HTTP handlers stay small; orchestration and I/O live in services and LangGraph nodes (backend DESIGN expands this).

---

## Known limitations / improvement areas

These are acknowledged gaps in the current design (see chat/PR discussions for detail):

- **Migrations are transitional** — fresh databases still get their schema from `SQLModel.metadata.create_all()` at startup; Alembic (`backend/migrations/`) handles incremental changes to existing databases. Migrations are run as an explicit deploy step (`make migrate ENV=<environment>`), not on container startup, and are written defensively (no-op if the target table doesn't exist yet). Long term, the schema should be fully owned by Alembic and `create_all()` removed. `backend/schema.sql` is stale.
- **No token revocation** — logout is client-side only; session JWTs remain valid until expiry. Tokens live in `localStorage` (XSS exposure); HttpOnly cookies are deferred (see auth redesign doc).
- **Singleton state** (`LangGraphAgent`, caches) assumes a single backend instance; horizontal scaling on Cloud Run requires externalizing or making this state safe.

When extending the system, update the relevant **DESIGN.md** in the same change as behavior that establishes a new pattern (new router prefix, new client service boundary, etc.).
