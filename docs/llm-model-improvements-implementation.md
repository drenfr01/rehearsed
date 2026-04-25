# LLM model improvements: implementation guide

**Design doc:** [llm-model-improvements.md](./llm-model-improvements.md)

This document provides step-by-step implementation instructions for the LLM factory and configurable model names changes. Steps are ordered so the codebase compiles and tests pass after each phase. Phases 1 and 2 are independent and can be implemented in parallel or in any order.

---

## Phase 1 — LLM chat factory

### Step 1.1: Create `backend/app/core/llm.py`

New file. Contains `_get_model_kwargs` (moved from `LangGraphAgent._get_model_kwargs`) and the `create_chat_llm` factory:

```python
"""Centralized LLM chat model factory.

All ChatGoogleGenerativeAI construction goes through create_chat_llm
so that Vertex kwargs, environment-specific tuning, and tool binding
are configured in one place.
"""

from typing import Any, Dict

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import Environment, settings
from app.core.langgraph.tools import tools


def _get_model_kwargs() -> Dict[str, Any]:
    """Return environment-specific model kwargs."""
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
    """Create a configured ChatGoogleGenerativeAI instance.

    Args:
        model_name: The Gemini model name (e.g. "gemini-3-flash-preview").
        bind_tools: If True, bind the LangGraph tool definitions to the model.

    Returns:
        A BaseChatModel ready for invocation.
    """
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

### Step 1.2: Refactor `backend/app/core/langgraph/graph_entry.py`

Four changes in this file.

**1.2a — Update imports.** Remove `ChatGoogleGenerativeAI`; add `create_chat_llm`:

Replace:

```python
from langchain_google_genai import ChatGoogleGenerativeAI
```

with:

```python
from app.core.llm import create_chat_llm
```

Also remove the `tools` import since it's no longer used directly in this file:

```python
from app.core.langgraph.tools import tools
```

**1.2b — Replace `_create_llm`.** Replace the method (currently lines 71–85):

```python
def _create_llm(self, model_name: str, bind_tools_flag: bool = False) -> ChatGoogleGenerativeAI:
    """Create a ChatGoogleGenerativeAI instance for a given model name."""
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=settings.DEFAULT_LLM_TEMPERATURE,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
        max_tokens=settings.MAX_TOKENS,
        vertexai=True,
        google_api_key=None,
        **self._get_model_kwargs(),
    )
    if bind_tools_flag:
        llm = llm.bind_tools(tools)
    return llm
```

with a thin delegator:

```python
def _create_llm(self, model_name: str, bind_tools_flag: bool = False) -> BaseChatModel:
    """Create a chat LLM instance via the centralized factory."""
    return create_chat_llm(model_name, bind_tools=bind_tools_flag)
```

Add `BaseChatModel` to the existing `langchain_core.messages` import block, or add a standalone import:

```python
from langchain_core.language_models import BaseChatModel
```

This preserves all call sites that reference `self._create_llm(...)` — the lazy properties, `_ensure_llms_from_config`, and `rebuild_graph` all continue working unchanged.

**1.2c — Delete `_get_model_kwargs`.** Remove the entire method (currently lines 185–203):

```python
def _get_model_kwargs(self) -> Dict[str, Any]:
    """Get environment-specific model kwargs.

    Returns:
        Dict[str, Any]: Additional model arguments based on environment
    """
    model_kwargs = {}

    # Development - we can use lower speeds for cost savings
    if settings.ENVIRONMENT == Environment.DEVELOPMENT:
        model_kwargs["top_p"] = 0.8

    # Production - use higher quality settings
    elif settings.ENVIRONMENT == Environment.PRODUCTION:
        model_kwargs["top_p"] = 0.95
        model_kwargs["presence_penalty"] = 0.1
        model_kwargs["frequency_penalty"] = 0.1

    return model_kwargs
```

With `_create_llm` now delegating to the factory, this method has no remaining callers.

**1.2d — Clean up `__init__` type hints.** The four `Optional[ChatGoogleGenerativeAI]` annotations in `__init__` (lines 60–63) should change to `Optional[BaseChatModel]`:

```python
self._llm_student: Optional[BaseChatModel] = None
self._llm_student_choice: Optional[BaseChatModel] = None
self._llm_inline_feedback: Optional[BaseChatModel] = None
self._llm_summary_feedback: Optional[BaseChatModel] = None
```

After this step, `ChatGoogleGenerativeAI` no longer appears anywhere in `graph_entry.py`.

### Step 1.3: Fix `_chat` fallback bug

Replace the `_chat` method body (currently lines 256–307). The key changes are:

1. Introduce a `current_llm` local variable initialized to `self.llm`.
2. On fallback, create a throwaway via `create_chat_llm` instead of mutating the singleton.
3. Fix the stale `models/` prefix on the fallback model name.
4. Fix the success log to report the actual model used.

Replace:

```python
@observe(name="chat_llm_call")
async def _chat(self, state: GraphState) -> dict:
    """Process the chat state and generate a response.

    Args:
        state (GraphState): The current state of the conversation.

    Returns:
        dict: Updated state with new messages.
    """
    messages = prepare_messages(state.messages, self.llm)

    llm_calls_num = 0

    # Configure retry attempts based on environment
    max_retries = settings.MAX_LLM_CALL_RETRIES

    for attempt in range(max_retries):
        try:
            with llm_inference_duration_seconds.labels(model=self.llm.model).time():
                generated_state = {"messages": [await self.llm.ainvoke(dump_messages(messages))]}
            logger.info(
                "llm_response_generated",
                session_id=state.session_id,
                llm_calls_num=llm_calls_num + 1,
                model=settings.LLM_MODEL,
                environment=settings.ENVIRONMENT.value,
            )
            return generated_state
        # TODO: make this a specific exception
        except Exception as e:
            logger.error(
                "llm_call_failed",
                llm_calls_num=llm_calls_num,
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e),
                environment=settings.ENVIRONMENT.value,
            )
            llm_calls_num += 1

            # In production, we might want to fall back to a more reliable model
            if settings.ENVIRONMENT == Environment.PRODUCTION and attempt == max_retries - 2:
                fallback_model = "models/gemini-3-flash-preview"
                logger.warning(
                    "using_fallback_model", model=fallback_model, environment=settings.ENVIRONMENT.value
                )
                self.llm.model = fallback_model

            continue

    raise Exception(f"Failed to get a response from the LLM after {max_retries} attempts")
```

with:

```python
@observe(name="chat_llm_call")
async def _chat(self, state: GraphState) -> dict:
    """Process the chat state and generate a response.

    Args:
        state (GraphState): The current state of the conversation.

    Returns:
        dict: Updated state with new messages.
    """
    messages = prepare_messages(state.messages, self.llm)
    current_llm = self.llm

    max_retries = settings.MAX_LLM_CALL_RETRIES

    for attempt in range(max_retries):
        try:
            with llm_inference_duration_seconds.labels(model=current_llm.model).time():
                generated_state = {"messages": [await current_llm.ainvoke(dump_messages(messages))]}
            logger.info(
                "llm_response_generated",
                session_id=state.session_id,
                attempt=attempt + 1,
                model=current_llm.model,
                environment=settings.ENVIRONMENT.value,
            )
            return generated_state
        except Exception as e:
            logger.error(
                "llm_call_failed",
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e),
                environment=settings.ENVIRONMENT.value,
            )

            if settings.ENVIRONMENT == Environment.PRODUCTION and attempt == max_retries - 2:
                fallback_model = "gemini-3-flash-preview"
                logger.warning(
                    "using_fallback_model", model=fallback_model, environment=settings.ENVIRONMENT.value
                )
                current_llm = create_chat_llm(fallback_model, bind_tools=True)

            continue

    raise Exception(f"Failed to get a response from the LLM after {max_retries} attempts")
```

### Step 1.4: Refactor `backend/app/services/summary_feedback.py`

Replace the `ChatGoogleGenerativeAI` import and hardcoded fallback with the factory and a DB-resolved model name.

**1.4a — Update imports.** Replace:

```python
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
```

with:

```python
from app.core.config import settings
from app.core.llm import create_chat_llm
from app.core.logging import logger
```

(`logger` is already imported; listed here for clarity.)

**1.4b — Replace the `llm is None` block.** Replace lines 61–70:

```python
if llm is None:
    llm = ChatGoogleGenerativeAI(
        model="gemini-3-pro-preview",
        temperature=settings.DEFAULT_LLM_TEMPERATURE,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
        max_tokens=settings.MAX_TOKENS,
        vertexai=True,
        google_api_key=None,
    )
```

with:

```python
if llm is None:
    model_name = settings.LLM_MODEL
    try:
        resolved = await database_service.agent_llm_config.get_model_name_for_agent(
            "summary_feedback"
        )
        if resolved:
            model_name = resolved
    except Exception as e:
        logger.warning(
            "summary_feedback_model_resolution_failed", error=str(e)
        )
    llm = create_chat_llm(model_name)
```

This resolves the model name from the same DB config that the LangGraph roles use, falling back to `settings.LLM_MODEL` if the DB lookup fails or returns `None`.

### Step 1.5: Clean up `backend/app/core/langgraph/graph.py`

Remove the unused import on line 12:

```python
from langchain_google_genai import ChatGoogleGenerativeAI
```

No other changes needed — the builder already types its LLM parameters as `BaseChatModel`.

---

## Phase 2 — Environment-variable model config

### Step 2.1: Add settings to `backend/app/core/config.py`

In the LangGraph Configuration block, after the `MAX_LLM_CALL_RETRIES` line (currently line 158), add:

```python
self.GEMINI_LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-live-2.5-flash-native-audio")
self.TTS_MODEL = os.getenv("TTS_MODEL", "gemini-2.5-flash-tts")
```

### Step 2.2: Add env vars to `.env` files

Add these two lines to `backend/.env`, `backend/.env.development`, and `backend/.env.production` (in the GCP configuration area, after the `GOOGLE_CLOUD_LOCATION` line):

```
GEMINI_LIVE_MODEL="gemini-live-2.5-flash-native-audio"
TTS_MODEL="gemini-2.5-flash-tts"
```

### Step 2.3: Refactor `backend/app/services/gemini_live.py`

**2.3a — Remove the module constant.** Delete line 26:

```python
GEMINI_LIVE_MODEL = "gemini-live-2.5-flash-native-audio"
```

**2.3b — Replace references.** There are two references in the `connect` method:

Line 76 — replace `model=GEMINI_LIVE_MODEL` with `model=settings.GEMINI_LIVE_MODEL`:

```python
self._context_manager = self._client.aio.live.connect(
    model=settings.GEMINI_LIVE_MODEL,
    config=config,
)
```

Line 84 — replace the log reference:

```python
logger.info(
    "gemini_live_session_connected",
    session_id=self.session_id,
    model=settings.GEMINI_LIVE_MODEL,
)
```

### Step 2.4: Refactor `backend/app/api/v1/gemini_live.py`

**2.4a — Update imports.** Replace:

```python
from app.services.gemini_live import (
    GEMINI_LIVE_MODEL,
    GeminiLiveSession,
    build_one_on_one_system_prompt,
)
```

with:

```python
from app.core.config import settings
from app.services.gemini_live import (
    GeminiLiveSession,
    build_one_on_one_system_prompt,
)
```

(`settings` may already be imported via another path — check and avoid duplicate imports. If `app.core.config` is not already imported, add it.)

**2.4b — Replace references.** Three locations:

Line 147 (trace metadata):

```python
"model": settings.GEMINI_LIVE_MODEL,
```

Line 208 (Langfuse observation):

```python
model=settings.GEMINI_LIVE_MODEL,
```

### Step 2.5: Refactor `backend/app/services/gemini_text_to_speech.py`

**2.5a — Add the settings import** at the top of the file:

```python
from app.core.config import settings
```

**2.5b — Change the default parameter.** Replace line 34:

```python
model_name: str = "gemini-2.5-flash-tts",
```

with:

```python
model_name: str | None = None,
```

And at the start of the method body, resolve the default:

```python
if model_name is None:
    model_name = settings.TTS_MODEL
```

**Why not `model_name: str = settings.TTS_MODEL` directly?** Default parameter values are evaluated once at import time. Since `settings` is a module-level singleton created at import, it would technically work here. However, using `None` with a body-level resolution is safer — it avoids subtle bugs if `settings` is ever lazy-loaded or if tests patch `settings.TTS_MODEL` after import. This follows the same defensive pattern used by `gemini_live.py`'s per-request resolution.

Update the docstring for `model_name` to reflect the new default source:

```python
model_name: The model to use for synthesis. Defaults to settings.TTS_MODEL.
```

---

## Phase 3 — Test updates

### Step 3.1: Create `backend/tests/unit/test_core/test_llm.py`

New test file covering the factory and environment kwargs:

```python
"""Unit tests for the LLM chat factory."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestGetModelKwargs:
    """Test _get_model_kwargs returns correct kwargs per environment."""

    def test_development_kwargs(self):
        with patch("app.core.llm.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "development"
            # Import after patching
            from app.core.llm import _get_model_kwargs, Environment

            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT
            result = _get_model_kwargs()
            assert result == {"top_p": 0.8}

    def test_production_kwargs(self):
        with patch("app.core.llm.settings") as mock_settings:
            from app.core.llm import _get_model_kwargs, Environment

            mock_settings.ENVIRONMENT = Environment.PRODUCTION
            result = _get_model_kwargs()
            assert result == {
                "top_p": 0.95,
                "presence_penalty": 0.1,
                "frequency_penalty": 0.1,
            }

    def test_test_env_returns_empty(self):
        with patch("app.core.llm.settings") as mock_settings:
            from app.core.llm import _get_model_kwargs, Environment

            mock_settings.ENVIRONMENT = Environment.TEST
            result = _get_model_kwargs()
            assert result == {}

    def test_staging_returns_empty(self):
        with patch("app.core.llm.settings") as mock_settings:
            from app.core.llm import _get_model_kwargs, Environment

            mock_settings.ENVIRONMENT = Environment.STAGING
            result = _get_model_kwargs()
            assert result == {}


@pytest.mark.unit
class TestCreateChatLlm:
    """Test create_chat_llm factory function."""

    def test_creates_with_expected_params(self):
        with (
            patch("app.core.llm.ChatGoogleGenerativeAI") as mock_llm_class,
            patch("app.core.llm.settings") as mock_settings,
            patch("app.core.llm._get_model_kwargs", return_value={}),
        ):
            mock_settings.DEFAULT_LLM_TEMPERATURE = 0.2
            mock_settings.GOOGLE_CLOUD_PROJECT = "test-project"
            mock_settings.GOOGLE_CLOUD_LOCATION = "us-central1"
            mock_settings.MAX_TOKENS = 200000
            mock_llm_class.return_value = MagicMock()

            from app.core.llm import create_chat_llm

            create_chat_llm("gemini-3-flash-preview")

            mock_llm_class.assert_called_once_with(
                model="gemini-3-flash-preview",
                temperature=0.2,
                project="test-project",
                location="us-central1",
                max_tokens=200000,
                vertexai=True,
                google_api_key=None,
            )

    def test_bind_tools_called_when_requested(self):
        with (
            patch("app.core.llm.ChatGoogleGenerativeAI") as mock_llm_class,
            patch("app.core.llm.settings") as mock_settings,
            patch("app.core.llm._get_model_kwargs", return_value={}),
        ):
            mock_settings.DEFAULT_LLM_TEMPERATURE = 0.2
            mock_settings.GOOGLE_CLOUD_PROJECT = "test-project"
            mock_settings.GOOGLE_CLOUD_LOCATION = "us-central1"
            mock_settings.MAX_TOKENS = 200000
            mock_instance = MagicMock()
            mock_llm_class.return_value = mock_instance

            from app.core.llm import create_chat_llm

            create_chat_llm("gemini-3-flash-preview", bind_tools=True)

            mock_instance.bind_tools.assert_called_once()

    def test_bind_tools_not_called_by_default(self):
        with (
            patch("app.core.llm.ChatGoogleGenerativeAI") as mock_llm_class,
            patch("app.core.llm.settings") as mock_settings,
            patch("app.core.llm._get_model_kwargs", return_value={}),
        ):
            mock_settings.DEFAULT_LLM_TEMPERATURE = 0.2
            mock_settings.GOOGLE_CLOUD_PROJECT = "test-project"
            mock_settings.GOOGLE_CLOUD_LOCATION = "us-central1"
            mock_settings.MAX_TOKENS = 200000
            mock_instance = MagicMock()
            mock_llm_class.return_value = mock_instance

            from app.core.llm import create_chat_llm

            create_chat_llm("gemini-3-flash-preview")

            mock_instance.bind_tools.assert_not_called()
```

### Step 3.2: Update `backend/tests/unit/test_services/test_summary_feedback.py`

The existing tests patch `app.services.summary_feedback.ChatGoogleGenerativeAI`. After the refactor, that import no longer exists; the patch target changes to the factory.

**3.2a — Update patch targets.** In `test_generate_summary_feedback_success`, `test_generate_summary_feedback_llm_parse_failure`, `test_generate_summary_feedback_filters_empty_messages`: change:

```python
patch("app.services.summary_feedback.ChatGoogleGenerativeAI") as mock_llm_class,
```

to:

```python
patch("app.services.summary_feedback.create_chat_llm") as mock_factory,
```

And update the mock wiring from `mock_llm_class.return_value = mock_llm_instance` to `mock_factory.return_value = mock_llm_instance`.

**3.2b — Update `test_generate_summary_feedback_uses_correct_llm_params`.** This test currently asserts the exact `ChatGoogleGenerativeAI(...)` constructor kwargs. After the refactor, the function calls `create_chat_llm(model_name)` instead. Replace the test:

```python
async def test_generate_summary_feedback_uses_correct_llm_params(
    self, mock_feedback_config, sample_conversation, mock_summary_response
):
    """Test that the factory is called with the DB-resolved model name."""
    with (
        patch("app.services.summary_feedback.database_service") as mock_db,
        patch("app.services.summary_feedback.create_chat_llm") as mock_factory,
    ):
        mock_db.feedback.get_feedback_by_type = AsyncMock(
            return_value=mock_feedback_config
        )
        mock_db.agent_llm_config.get_model_name_for_agent = AsyncMock(
            return_value="gemini-3.1-pro-preview"
        )

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(
            return_value={"parsed": mock_summary_response, "raw": ""}
        )
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_chain
        mock_factory.return_value = mock_llm_instance

        from app.services.summary_feedback import generate_summary_feedback

        await generate_summary_feedback(1, sample_conversation)

        mock_factory.assert_called_once_with("gemini-3.1-pro-preview")
        mock_db.agent_llm_config.get_model_name_for_agent.assert_called_once_with(
            "summary_feedback"
        )
```

**3.2c — Add a test for DB resolution fallback:**

```python
async def test_generate_summary_feedback_falls_back_on_db_error(
    self, mock_feedback_config, sample_conversation, mock_summary_response
):
    """Test that settings.LLM_MODEL is used when DB resolution fails."""
    with (
        patch("app.services.summary_feedback.database_service") as mock_db,
        patch("app.services.summary_feedback.create_chat_llm") as mock_factory,
        patch("app.services.summary_feedback.settings") as mock_settings,
    ):
        mock_settings.LLM_MODEL = "gemini-3-flash-preview"

        mock_db.feedback.get_feedback_by_type = AsyncMock(
            return_value=mock_feedback_config
        )
        mock_db.agent_llm_config.get_model_name_for_agent = AsyncMock(
            side_effect=Exception("DB error")
        )

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(
            return_value={"parsed": mock_summary_response, "raw": ""}
        )
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_chain
        mock_factory.return_value = mock_llm_instance

        from app.services.summary_feedback import generate_summary_feedback

        await generate_summary_feedback(1, sample_conversation)

        mock_factory.assert_called_once_with("gemini-3-flash-preview")
```

### Step 3.3: Update `backend/tests/unit/test_services/test_gemini_live.py`

**3.3a — Update imports.** Replace:

```python
from app.services.gemini_live import (
    GEMINI_LIVE_LOCATION,
    GEMINI_LIVE_MODEL,
    GeminiLiveSession,
    build_one_on_one_system_prompt,
)
```

with:

```python
from app.services.gemini_live import (
    GEMINI_LIVE_LOCATION,
    GeminiLiveSession,
    build_one_on_one_system_prompt,
)
```

**3.3b — Update `test_constants`.** Replace:

```python
def test_constants(self):
    assert GEMINI_LIVE_MODEL == "gemini-live-2.5-flash-native-audio"
    assert GEMINI_LIVE_LOCATION == "us-central1"
```

with:

```python
def test_constants(self):
    from app.core.config import settings

    assert settings.GEMINI_LIVE_MODEL == "gemini-live-2.5-flash-native-audio"
    assert GEMINI_LIVE_LOCATION == "us-central1"
```

### Step 3.4: `backend/tests/unit/test_services/test_gemini_text_to_speech.py`

No structural changes needed. The existing `test_synthesize_async` calls without `model_name` (will use the new `settings.TTS_MODEL` default) and `test_synthesize_async_custom_model` passes an explicit `model_name="custom-model"`. Both continue to pass.

If desired, add a test that verifies the default model comes from settings:

```python
async def test_synthesize_async_uses_settings_default(self):
    """Test that the default model_name comes from settings.TTS_MODEL."""
    with patch("app.services.gemini_text_to_speech.settings") as mock_settings:
        mock_settings.TTS_MODEL = "gemini-2.5-flash-tts"

        service = GeminiTextToSpeech()
        mock_response = MagicMock()
        mock_response.audio_content = b"audio"
        mock_async_client = AsyncMock()
        mock_async_client.synthesize_speech = AsyncMock(return_value=mock_response)
        service._async_client = mock_async_client

        await service.synthesize_async(
            prompt="Prompt",
            text="Text",
            voice_name="Aoede",
        )

        call_kwargs = mock_async_client.synthesize_speech.call_args
        voice_arg = call_kwargs.kwargs.get("voice")
        assert voice_arg.model_name == "gemini-2.5-flash-tts"
```

---

## Phase 4 — Verification

### Step 4.1: Scan for remaining direct `ChatGoogleGenerativeAI` construction

Run a project-wide search to confirm no files outside of `app/core/llm.py` directly construct `ChatGoogleGenerativeAI`:

```bash
rg "ChatGoogleGenerativeAI(" backend/app/ --glob '!__pycache__'
```

Expected: only `app/core/llm.py` matches.

### Step 4.2: Scan for remaining hardcoded model names

```bash
rg '"gemini-live-2.5-flash-native-audio"' backend/app/
rg '"gemini-2.5-flash-tts"' backend/app/
rg '"gemini-3-pro-preview"' backend/app/
```

Expected:
- Gemini Live model string appears only in `config.py` as the env var default.
- TTS model string appears only in `config.py` as the env var default.
- `gemini-3-pro-preview` appears nowhere (replaced by DB-resolved model).

### Step 4.3: Manual verification checklist

| # | Check | What to verify |
|---|-------|---------------|
| 1 | **Factory parity** | LLM configuration per environment matches the old `_create_llm` + `_get_model_kwargs` output. Compare by logging or inspecting constructed instances in dev and production modes. |
| 2 | **Singleton preserved** | After multiple chat requests across different scenarios, `LangGraphAgent._llm_student` is the same object (not recreated per request). |
| 3 | **Fallback safety** | In production, trigger the retry fallback (e.g. by temporarily pointing the primary model at a non-existent name). Verify the singleton is not corrupted after the fallback completes — subsequent requests use the original model. |
| 4 | **Summary feedback standalone** | Call `POST /api/v1/gemini-live/summary-feedback` (which does not pass an `llm` argument). Verify it resolves the model from DB config, or falls back to `settings.LLM_MODEL` if no config exists. |
| 5 | **Gemini Live model** | Start a Gemini Live WebSocket session. Verify the Langfuse trace shows `settings.GEMINI_LIVE_MODEL` as the model. |
| 6 | **TTS model** | Trigger TTS synthesis. Verify the correct model is used in the Google Cloud TTS request. |
| 7 | **Env var override** | Set `GEMINI_LIVE_MODEL=gemini-3.1-flash-live-preview` in `.env`, restart, and verify the new model is used. Same for `TTS_MODEL`. |
| 8 | **Admin config change** | Change the summary feedback model via the admin LLM config UI. Verify `invalidate_llms()` is called and the next request uses the new model. |

### Step 4.4: Run existing test suites

```bash
cd backend && python -m pytest tests/unit/ -x -q
cd backend && python -m pytest tests/integration/ -x -q
```

All tests should pass. If any test still patches `ChatGoogleGenerativeAI` in a file where it was removed, update the patch target to `app.core.llm.create_chat_llm` or `app.core.llm.ChatGoogleGenerativeAI` as appropriate.
