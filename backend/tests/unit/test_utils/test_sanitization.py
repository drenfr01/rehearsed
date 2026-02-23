"""Unit tests for sanitization utilities."""

import pytest

from app.utils.sanitization import (
    sanitize_dict,
    sanitize_email,
    sanitize_list,
    sanitize_string,
    validate_password_strength,
)


@pytest.mark.unit
class TestSanitizeString:
    """Test sanitize_string function."""

    def test_sanitize_string_normal_input(self):
        result = sanitize_string("Hello World")
        assert result == "Hello World"

    def test_sanitize_string_strips_whitespace(self):
        result = sanitize_string("  Hello World  ")
        assert result == "Hello World"

    def test_sanitize_string_empty_string(self):
        result = sanitize_string("")
        assert result == ""

    def test_sanitize_string_removes_script_tags(self):
        result = sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result.lower()

    def test_sanitize_string_html_escapes(self):
        result = sanitize_string("<b>bold</b>")
        assert "&lt;b&gt;" in result

    def test_sanitize_string_removes_null_bytes(self):
        result = sanitize_string("Hello\0World")
        assert "\0" not in result

    def test_sanitize_string_non_string_input(self):
        result = sanitize_string(123)
        assert isinstance(result, str)

    def test_sanitize_string_preserves_alphanumeric(self):
        result = sanitize_string("abc123")
        assert result == "abc123"


@pytest.mark.unit
class TestSanitizeEmail:
    """Test sanitize_email function."""

    def test_sanitize_email_valid(self):
        result = sanitize_email("test@example.com")
        assert result == "test@example.com"

    def test_sanitize_email_with_whitespace(self):
        result = sanitize_email("  Test@Example.COM  ")
        assert result == "test@example.com"

    def test_sanitize_email_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid email format"):
            sanitize_email("not-an-email")

    def test_sanitize_email_lowercases(self):
        result = sanitize_email("USER@DOMAIN.COM")
        assert result == "user@domain.com"

    def test_sanitize_email_with_plus(self):
        result = sanitize_email("user+tag@example.com")
        assert result == "user+tag@example.com"

    def test_sanitize_email_missing_at(self):
        with pytest.raises(ValueError):
            sanitize_email("nodomain")

    def test_sanitize_email_missing_domain(self):
        with pytest.raises(ValueError):
            sanitize_email("user@")


@pytest.mark.unit
class TestSanitizeDict:
    """Test sanitize_dict function."""

    def test_sanitize_dict_strings(self):
        data = {"name": "  Hello  ", "value": "Test"}
        result = sanitize_dict(data)
        assert result["name"] == "Hello"
        assert result["value"] == "Test"

    def test_sanitize_dict_nested_dict(self):
        data = {"outer": {"inner": "  Nested  "}}
        result = sanitize_dict(data)
        assert result["outer"]["inner"] == "Nested"

    def test_sanitize_dict_with_list(self):
        data = {"items": ["  a  ", "  b  "]}
        result = sanitize_dict(data)
        assert result["items"] == ["a", "b"]

    def test_sanitize_dict_non_string_values(self):
        data = {"count": 42, "active": True, "name": "Test"}
        result = sanitize_dict(data)
        assert result["count"] == 42
        assert result["active"] is True
        assert result["name"] == "Test"

    def test_sanitize_dict_html_in_values(self):
        data = {"content": "<script>alert('xss')</script>"}
        result = sanitize_dict(data)
        assert "<script>" not in result["content"].lower()

    def test_sanitize_dict_empty(self):
        assert sanitize_dict({}) == {}


@pytest.mark.unit
class TestSanitizeList:
    """Test sanitize_list function."""

    def test_sanitize_list_strings(self):
        data = ["  Hello  ", "  World  "]
        result = sanitize_list(data)
        assert result == ["Hello", "World"]

    def test_sanitize_list_nested_dict(self):
        data = [{"name": "  Test  "}]
        result = sanitize_list(data)
        assert result[0]["name"] == "Test"

    def test_sanitize_list_nested_list(self):
        data = [["  inner  "]]
        result = sanitize_list(data)
        assert result[0] == ["inner"]

    def test_sanitize_list_non_string(self):
        data = [42, True, None]
        result = sanitize_list(data)
        assert result == [42, True, None]

    def test_sanitize_list_empty(self):
        assert sanitize_list([]) == []

    def test_sanitize_list_mixed(self):
        data = ["  hello  ", 42, {"key": "  value  "}, ["  nested  "]]
        result = sanitize_list(data)
        assert result[0] == "hello"
        assert result[1] == 42
        assert result[2]["key"] == "value"
        assert result[3] == ["nested"]


@pytest.mark.unit
class TestValidatePasswordStrength:
    """Test validate_password_strength function."""

    def test_valid_strong_password(self):
        result = validate_password_strength("StrongPassword123!")
        assert result is True

    def test_too_short(self):
        with pytest.raises(ValueError, match="at least 8 characters"):
            validate_password_strength("Ab1!")

    def test_no_uppercase(self):
        with pytest.raises(ValueError, match="uppercase"):
            validate_password_strength("lowercase123!")

    def test_no_lowercase(self):
        with pytest.raises(ValueError, match="lowercase"):
            validate_password_strength("UPPERCASE123!")

    def test_no_number(self):
        with pytest.raises(ValueError, match="number"):
            validate_password_strength("NoNumberHere!")

    def test_no_special_character(self):
        with pytest.raises(ValueError, match="special character"):
            validate_password_strength("NoSpecial123")

    def test_exactly_8_characters(self):
        result = validate_password_strength("Ab1!xxxx")
        assert result is True
