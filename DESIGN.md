# Rehearsed — system design

Rehearsed is a **teacher simulation platform**: educators practice in AI-driven classroom scenarios (multi-student and one-on-one), with feedback and configurable content (scenarios, agents, personalities, voices, avatars).

This document is the **system-level** view. Implementation patterns and conventions live in:

- [frontend/DESIGN.md](frontend/DESIGN.md) — Angular SPA structure, routing, HTTP, and UI patterns  
- [backend/DESIGN.md](backend/DESIGN.md) — FastAPI layering, LangGraph, persistence, and API patterns  
- [docs/auth-redesign.md](docs/auth-redesign.md) — JWT hardening: typed tokens, secret validation, admin-claim changes  

---

## Architecture overview

| Layer | Technology | Responsibility |
|--------|------------|----------------|
| Client | Angular 20 + Material | Auth, scenario flows, classroom / 1:1 UI, admin and user-content CRUD, WebSocket for live Gemini where used |
| API | FastAPI | REST under `/api/v1`, JWT session, rate limits, CORS, metrics |
| Orchestration | LangGraph + LangChain (Vertex / Gemini) | Per-scenario conversation graph: appropriateness, student agents, inline/summary feedback |
| Data | PostgreSQL | Users, scenarios, agents, sessions/threads, feedback definitions, LLM config, avatars |
| Speech | Google Cloud (TTS / STT) + Gemini Live | Audio playback, optional live voice |
| Observability | Langfuse, Prometheus-style metrics | LLM traces, request metrics |

---

## Major data flows

1. **Teacher session (LangGraph / chatbot)**  
   Authenticated `POST /api/v1/chatbot/chat` drives a compiled graph for the current scenario. State includes messages, student turns, feedback, and goal-related flags. TTS audio may be generated and exposed via `/api/v1/tts/{id}`.

2. **Live voice (Gemini Live)**  
   WebSocket session derived from the API base URL; related HTTP endpoints for setup or summary feedback as implemented in `gemini_live` routes.

3. **Content management**  
   **Admin** routes manage global catalog entities. **User content** routes manage user-scoped scenarios, agents, personalities, and feedback. **Scenario** routes expose selection and per-scenario agents for the active simulation.

---

## Cross-cutting concerns

- **Authentication:** JWT bearer; session establishment pattern coordinated with the SPA (see frontend DESIGN for token handling).
- **Authorization:** Separate route trees for admin vs user content; handlers use `Depends(get_current_session)` or `get_current_user` as appropriate.
- **Configuration:** Environment-driven settings (CORS, rate limits, model names, GCP project/location). OpenAPI served at `{API_V1_STR}/openapi.json`.
- **Resilience:** LangGraph node `RetryPolicy` for transient LLM failures; rate limiting on hot endpoints.

---

## Repository layout (conceptual)

```
rehearsed/
├── frontend/     # Angular SPA — see frontend/DESIGN.md
├── backend/      # FastAPI + LangGraph — see backend/DESIGN.md
└── DESIGN.md     # This file
```

---

## Design principles (product + engineering)

1. **Scenario-centric simulation** — The graph and agent roster are built from the selected scenario’s data in the database, not hard-coded student count.
2. **API-first** — The SPA is a client of versioned REST; contracts should stay aligned with OpenAPI and shared schema names where possible.
3. **Observable AI** — LLM-heavy paths are instrumented (e.g. Langfuse) so regressions and cost can be traced per environment.
4. **Thin transport, rich domain** — HTTP handlers stay small; orchestration and I/O live in services and LangGraph nodes (backend DESIGN expands this).

When extending the system, update the relevant **DESIGN.md** in the same change as behavior that establishes a new pattern (new router prefix, new client service boundary, etc.).
