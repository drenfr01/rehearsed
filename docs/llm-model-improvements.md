# LLM model improvements: factory and configurable model names

**Status:** Proposed  
**Related docs:** [System design](../DESIGN.md) | [Backend design](../backend/DESIGN.md) | [Implementation guide](./llm-model-improvements-implementation.md)

---

## 1. Motivation

The backend uses Gemini models in several distinct subsystems — LangGraph classroom simulation, summary feedback generation, Gemini Live voice sessions, and TTS synthesis. Each subsystem instantiates its Google client independently, leading to two problems:

| # | Issue | Impact |
|---|-------|--------|
| 1 | **Duplicated LLM instantiation** | `ChatGoogleGenerativeAI` is constructed with identical Vertex/project/location kwargs in `graph_entry.py` and `summary_feedback.py`. Adding cross-cutting behavior (observability, environment-specific tuning) means patching every site. |
| 2 | **Hardcoded model names in source** | Gemini Live (`gemini-live-2.5-flash-native-audio` in `gemini_live.py`), TTS (`gemini-2.5-flash-tts` in `gemini_text_to_speech.py`), and the summary feedback fallback (`gemini-3-pro-preview`) are string literals in code. Changing any of them requires a code change and redeploy instead of an env-var or config update. |
| 3 | **Production fallback mutates shared LLM singleton** | `_chat()` in `graph_entry.py` sets `self.llm.model = fallback_model` on retry failure, permanently corrupting the shared `_llm_student` instance for all subsequent requests until the process restarts. |

This document describes two changes that address these issues.

---

## 2. Goals and non-goals

### Goals

- Centralize all `ChatGoogleGenerativeAI` construction behind a single factory function, including environment-specific model kwargs.
- Make Gemini Live and TTS model names configurable via environment variables, eliminating hardcoded constants scattered across service files.
- Eliminate the hardcoded summary feedback fallback model.
- Fix the production fallback bug in `_chat()` that permanently corrupts the shared LLM singleton.

### Non-goals

- Multi-provider support (Anthropic, OpenAI). The factory uses `ChatGoogleGenerativeAI` only. `LangGraphBuilder` already accepts `BaseChatModel`, so adding providers later does not require rearchitecting the graph layer.
- Context caching (Vertex cached content). The system prompts used in this application are generally below Gemini's 32K-token minimum for context caching, and the conversational content that might exceed it is dynamic per-turn — a poor fit for prefix caching. This can be revisited if prompt sizes grow.
- Frontend changes. Gemini Live and TTS model names are environment variables, not DB-backed, so no admin UI changes are needed.

---

## 3. Design

### 3.1 LLM chat factory

**New file: `app/core/llm.py`**

A single factory function replaces all direct `ChatGoogleGenerativeAI` construction:

```python
from typing import Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel

from app.core.config import Environment, settings
from app.core.langgraph.tools import tools


def _get_model_kwargs() -> Dict[str, Any]:
    """Return environment-specific model kwargs.

    Preserves the per-environment tuning that was previously in
    ``LangGraphAgent._get_model_kwargs``.
    """
    if settings.ENVIRONMENT == Environment.DEVELOPMENT:
        return {"top_p": 0.8}
    if settings.ENVIRONMENT == Environment.PRODUCTION:
        return {
            "top_p": 0.95,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.1,
        }
    return {}


def create_chat_llm(
    model_name: str,
    *,
    bind_tools: bool = False,
) -> BaseChatModel:
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=settings.DEFAULT_LLM_TEMPERATURE,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
        max_tokens=settings.MAX_TOKENS,
        vertexai=True,
        google_api_key=None,
        **_get_model_kwargs(),
    )
    if bind_tools:
        llm = llm.bind_tools(tools)
    return llm
```

**Consumers to refactor:**

| File | Current behavior | After |
|------|-----------------|-------|
| `graph_entry.py` `_create_llm` | Constructs `ChatGoogleGenerativeAI` with Vertex kwargs and its own `_get_model_kwargs` | Delete `_create_llm` and `_get_model_kwargs`. Replace all call sites with direct `create_chat_llm(...)` calls. Remove `ChatGoogleGenerativeAI` import. |
| `graph_entry.py` `_chat` fallback | Mutates `self.llm.model` on the shared singleton (see 3.1.1 below) | Creates a throwaway instance via `create_chat_llm` for the final retry. |
| `summary_feedback.py` `llm=None` path | Hardcodes `ChatGoogleGenerativeAI(model="gemini-3-pro-preview", ...)` | Resolves model name from DB via `get_model_name_for_agent("summary_feedback")` with `settings.LLM_MODEL` fallback, then calls `create_chat_llm`. |
| `graph.py` | Unused `ChatGoogleGenerativeAI` import | Remove import. No other changes (already typed as `BaseChatModel`). |

#### 3.1.1 Fix: production fallback in `_chat` corrupts shared LLM singleton

`LangGraphAgent._chat` has a production-only retry path that falls back to a different model on the penultimate attempt:

```python
# Current code (graph_entry.py, _chat method)
if settings.ENVIRONMENT == Environment.PRODUCTION and attempt == max_retries - 2:
    fallback_model = "models/gemini-3-flash-preview"
    self.llm.model = fallback_model  # BUG: mutates the shared singleton
```

`self.llm` is the `_llm_student` singleton shared across all scenarios and requests. Mutating its `.model` attribute permanently switches every subsequent LLM call to the fallback model for the lifetime of the process. The only recovery is a full restart.

**Fix:** Use the factory to create a local, throwaway LLM instance for the retry. A `current_llm` local variable starts as `self.llm`; on fallback, it is reassigned to a fresh `create_chat_llm(...)` instance. The shared singleton is never touched.

`prepare_messages` must also use `current_llm` rather than `self.llm`. It passes the LLM as a `token_counter` to LangChain's `trim_messages`, so if the fallback fires and a different model is used for invocation, the token counts would be computed against the wrong tokenizer. Moving `prepare_messages` inside the loop and passing `current_llm` keeps token counting and invocation consistent. This is safe because `prepare_messages` is a pure function and cheap relative to the LLM call.

The fallback model name is read from `settings.LLM_FALLBACK_MODEL` (see 3.2) rather than hardcoded, so it can be changed via an env-var update and restart.

```python
current_llm = self.llm
max_retries = settings.MAX_LLM_CALL_RETRIES

for attempt in range(max_retries):
    try:
        messages = prepare_messages(state.messages, current_llm)
        result = await current_llm.ainvoke(dump_messages(messages))
        return {"messages": [result]}
    except Exception:
        if settings.ENVIRONMENT == Environment.PRODUCTION and attempt == max_retries - 2:
            current_llm = create_chat_llm(settings.LLM_FALLBACK_MODEL, bind_tools=True)
        continue
```

Also fixes three incidental issues in the same method:
- The fallback model name has a stale `models/` prefix (`models/gemini-3-flash-preview`) that doesn't match the naming convention used everywhere else — now read from `settings.LLM_FALLBACK_MODEL`.
- The success log reports `model=settings.LLM_MODEL` instead of the model that actually produced the response — corrected to `model=current_llm.model`.
- `prepare_messages` was called once before the loop with `self.llm`, creating a tokenizer mismatch if the fallback model was used for invocation — now called per-attempt with `current_llm`.

#### 3.1.2 LLM instance lifecycle: 4 singletons, not per-scenario

The factory does **not** change the existing singleton lifecycle. `_ensure_llms_from_config` continues to create exactly one LLM instance per role (student, student-choice, inline-feedback, summary-feedback), shared across all scenarios. The `_graphs` cache holds compiled `StateGraph` objects per `scenario_id`, but every graph references the same 4 LLM instances.

When an admin changes the LLM configuration, `invalidate_llms()` clears all 4 instance slots and the graph cache. The next request re-resolves model names from the database and creates fresh instances via the factory.

This is a deliberate tradeoff: per-scenario LLM instances (one per scenario per role) would allow scenario-specific model selection but at the cost of unbounded instance growth, more complex invalidation, and no current product requirement. If per-scenario models become necessary, the graph cache already keys by `scenario_id` and could hold scenario-scoped LLM references — but that change should be designed separately.

### 3.2 Environment-variable config for Gemini Live and TTS model names

Gemini Live and TTS use entirely different SDKs (`google.genai` and `google.cloud.texttospeech`) — they are not LangChain chat models and are not "agents" in the simulation sense. Extending the `agent_llm_config` DB table to cover them would overload the `AgentType` enum, require a Postgres enum migration, and add DB round-trips for services that have no other reason to query `agent_llm_config`.

Instead, these model names become environment variables in `app/core/config.py`, following the same pattern as `LLM_MODEL` and `LLM_ANSWERING_STUDENT_MODEL`.

**New settings in `app/core/config.py`:**

```python
self.LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "gemini-3-flash-preview")
self.GEMINI_LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-live-2.5-flash-native-audio")
self.TTS_MODEL = os.getenv("TTS_MODEL", "gemini-2.5-flash-tts")
```

**Consumer changes:**

| File | Current | After |
|------|---------|-------|
| `gemini_live.py` | `GEMINI_LIVE_MODEL = "gemini-live-2.5-flash-native-audio"` module constant | Replace with `settings.GEMINI_LIVE_MODEL`. Remove the module-level constant. |
| `gemini_text_to_speech.py` | `model_name: str = "gemini-2.5-flash-tts"` default parameter | Default to `settings.TTS_MODEL` instead of the hardcoded string. |
| `gemini_live.py` (router) | Imports `GEMINI_LIVE_MODEL` from the service module | Import `settings` instead. |

Switching models requires setting the env var and restarting. This matches the operational model for all other non-DB LLM settings and avoids adding DB schema changes for what is fundamentally a deployment-time configuration choice.

---

## 4. Implementation order

Areas 1 and 2 are independent and can be implemented in parallel.

```
Area 1 (factory)
Area 2 (env-var config)
```

**Area 1 — LLM chat factory:**
1. Create `app/core/llm.py` with `_get_model_kwargs` and `create_chat_llm`.
2. Refactor `graph_entry.py`: delete `_create_llm` and `_get_model_kwargs`, replace all call sites with direct `create_chat_llm(...)` calls.
3. Refactor `summary_feedback.py` `llm=None` fallback to use the factory with DB-resolved model name.
4. Remove unused `ChatGoogleGenerativeAI` import from `graph.py`.

**Area 2 — Environment-variable model config:**
1. Add `LLM_FALLBACK_MODEL`, `GEMINI_LIVE_MODEL`, and `TTS_MODEL` to `app/core/config.py`.
2. Add the new env vars to `.env`, `.env.development`, and `.env.production`.
3. Refactor `gemini_live.py` to use `settings.GEMINI_LIVE_MODEL` instead of the module constant.
4. Refactor `gemini_text_to_speech.py` to default to `settings.TTS_MODEL`.

---

## 5. Files changed

| File | Change type |
|------|-------------|
| `app/core/llm.py` | New — factory function with environment-specific kwargs |
| `app/core/langgraph/graph_entry.py` | Modified — replace all `_create_llm` call sites with direct `create_chat_llm` calls, delete `_create_llm` and `_get_model_kwargs` |
| `app/core/langgraph/graph.py` | Modified — remove unused import |
| `app/services/summary_feedback.py` | Modified — use factory with DB-resolved model |
| `app/core/config.py` | Modified — add `LLM_FALLBACK_MODEL`, `GEMINI_LIVE_MODEL`, and `TTS_MODEL` settings |
| `app/services/gemini_live.py` | Modified — use `settings.GEMINI_LIVE_MODEL`, remove module constant |
| `app/services/gemini_text_to_speech.py` | Modified — default to `settings.TTS_MODEL` |
