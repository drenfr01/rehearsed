"""Unit tests for application configuration."""

import os
from unittest.mock import patch

import pytest

from app.core.config import (
    Environment,
    get_environment,
    parse_dict_of_lists_from_env,
    parse_list_from_env,
)


@pytest.mark.unit
class TestEnvironmentEnum:
    """Test Environment enum."""

    def test_development_value(self):
        assert Environment.DEVELOPMENT.value == "development"

    def test_staging_value(self):
        assert Environment.STAGING.value == "staging"

    def test_production_value(self):
        assert Environment.PRODUCTION.value == "production"

    def test_test_value(self):
        assert Environment.TEST.value == "test"

    def test_enum_is_string(self):
        assert isinstance(Environment.DEVELOPMENT, str)
        assert Environment.PRODUCTION == "production"


@pytest.mark.unit
class TestGetEnvironment:
    """Test get_environment function."""

    def test_default_is_development(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove APP_ENV entirely
            os.environ.pop("APP_ENV", None)
            assert get_environment() == Environment.DEVELOPMENT

    def test_production_env(self):
        with patch.dict(os.environ, {"APP_ENV": "production"}):
            assert get_environment() == Environment.PRODUCTION

    def test_prod_shorthand(self):
        with patch.dict(os.environ, {"APP_ENV": "prod"}):
            assert get_environment() == Environment.PRODUCTION

    def test_staging_env(self):
        with patch.dict(os.environ, {"APP_ENV": "staging"}):
            assert get_environment() == Environment.STAGING

    def test_stage_shorthand(self):
        with patch.dict(os.environ, {"APP_ENV": "stage"}):
            assert get_environment() == Environment.STAGING

    def test_test_env(self):
        with patch.dict(os.environ, {"APP_ENV": "test"}):
            assert get_environment() == Environment.TEST

    def test_case_insensitive(self):
        with patch.dict(os.environ, {"APP_ENV": "PRODUCTION"}):
            assert get_environment() == Environment.PRODUCTION

    def test_unknown_defaults_to_development(self):
        with patch.dict(os.environ, {"APP_ENV": "unknown"}):
            assert get_environment() == Environment.DEVELOPMENT


@pytest.mark.unit
class TestParseListFromEnv:
    """Test parse_list_from_env function."""

    def test_comma_separated_values(self):
        with patch.dict(os.environ, {"TEST_LIST": "a, b, c"}):
            result = parse_list_from_env("TEST_LIST")
            assert result == ["a", "b", "c"]

    def test_single_value(self):
        with patch.dict(os.environ, {"TEST_LIST": "single"}):
            result = parse_list_from_env("TEST_LIST")
            assert result == ["single"]

    def test_empty_value_uses_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEST_LIST_MISSING", None)
            result = parse_list_from_env("TEST_LIST_MISSING", ["default"])
            assert result == ["default"]

    def test_no_default_returns_empty(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEST_LIST_NONE", None)
            result = parse_list_from_env("TEST_LIST_NONE")
            assert result == []

    def test_quoted_values(self):
        with patch.dict(os.environ, {"TEST_LIST": '"a, b, c"'}):
            result = parse_list_from_env("TEST_LIST")
            assert result == ["a", "b", "c"]

    def test_strips_whitespace(self):
        with patch.dict(os.environ, {"TEST_LIST": "  a  ,  b  ,  c  "}):
            result = parse_list_from_env("TEST_LIST")
            assert result == ["a", "b", "c"]

    def test_filters_empty_items(self):
        with patch.dict(os.environ, {"TEST_LIST": "a,,b,,c"}):
            result = parse_list_from_env("TEST_LIST")
            assert result == ["a", "b", "c"]


@pytest.mark.unit
class TestParseDictOfListsFromEnv:
    """Test parse_dict_of_lists_from_env function."""

    def test_parses_prefixed_env_vars(self):
        with patch.dict(
            os.environ,
            {
                "RATE_LIMIT_CHAT": "30 per minute",
                "RATE_LIMIT_LOGIN": "5 per minute, 20 per hour",
            },
        ):
            result = parse_dict_of_lists_from_env("RATE_LIMIT_")
            assert "chat" in result
            assert result["chat"] == ["30 per minute"]
            assert "login" in result
            assert result["login"] == ["5 per minute", "20 per hour"]

    def test_uses_default_dict(self):
        default = {"chat": ["10 per minute"]}
        result = parse_dict_of_lists_from_env("NONEXISTENT_PREFIX_", default)
        assert result == {"chat": ["10 per minute"]}

    def test_empty_default(self):
        result = parse_dict_of_lists_from_env("NONEXISTENT_PREFIX_XYZ_")
        assert result == {}


@pytest.mark.unit
class TestSettings:
    """Test Settings class initialization."""

    def test_settings_creates_instance(self):
        from app.core.config import Settings

        with patch.dict(os.environ, {"APP_ENV": "test"}):
            s = Settings()
            assert s.ENVIRONMENT == Environment.TEST

    def test_settings_has_project_name(self):
        from app.core.config import Settings

        s = Settings()
        assert s.PROJECT_NAME is not None
        assert len(s.PROJECT_NAME) > 0

    def test_settings_has_jwt_config(self):
        from app.core.config import Settings

        s = Settings()
        assert s.JWT_ALGORITHM == "HS256"
        assert s.JWT_ACCESS_TOKEN_EXPIRE_DAYS > 0

    def test_settings_has_rate_limits(self):
        from app.core.config import Settings

        s = Settings()
        assert isinstance(s.RATE_LIMIT_DEFAULT, list)
        assert len(s.RATE_LIMIT_DEFAULT) > 0

    def test_settings_has_rate_limit_endpoints(self):
        from app.core.config import Settings

        s = Settings()
        assert "chat" in s.RATE_LIMIT_ENDPOINTS
        assert "login" in s.RATE_LIMIT_ENDPOINTS
        assert "register" in s.RATE_LIMIT_ENDPOINTS

    def test_test_environment_overrides(self):
        from app.core.config import Settings

        with patch.dict(os.environ, {"APP_ENV": "test"}):
            s = Settings()
            assert s.DEBUG is True
            assert s.LOG_LEVEL == "DEBUG"

    def test_production_environment_overrides(self):
        from app.core.config import Settings

        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=False):
            s = Settings()
            assert s.ENVIRONMENT == Environment.PRODUCTION
            assert s.DEBUG is False
