"""Unit tests for the LLM chat factory."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Environment
from app.core.llm import _get_model_kwargs, create_chat_llm


@pytest.mark.unit
class TestGetModelKwargs:
    """Test _get_model_kwargs returns correct kwargs per environment."""

    def test_development_kwargs(self):
        with patch("app.core.llm.settings") as mock_settings:
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT
            result = _get_model_kwargs()
            assert result == {"top_p": 0.8}

    def test_production_kwargs(self):
        with patch("app.core.llm.settings") as mock_settings:
            mock_settings.ENVIRONMENT = Environment.PRODUCTION
            result = _get_model_kwargs()
            assert result == {
                "top_p": 0.95,
                "presence_penalty": 0.1,
                "frequency_penalty": 0.1,
            }

    def test_test_env_returns_empty(self):
        with patch("app.core.llm.settings") as mock_settings:
            mock_settings.ENVIRONMENT = Environment.TEST
            result = _get_model_kwargs()
            assert result == {}

    def test_staging_returns_empty(self):
        with patch("app.core.llm.settings") as mock_settings:
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

            create_chat_llm("gemini-3-flash-preview")

            mock_instance.bind_tools.assert_not_called()
