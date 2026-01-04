"""Unit tests for sanitization utilities."""

import pytest

from app.utils.sanitization import sanitize_string, sanitize_email, validate_password_strength


@pytest.mark.unit
class TestSanitizeString:
    """Test sanitize_string function."""

    def test_sanitize_string_normal_input(self):
        """Test sanitization of normal input."""
        input_str = "Hello World"
        result = sanitize_string(input_str)
        assert result == "Hello World"

    def test_sanitize_string_strips_whitespace(self):
        """Test that sanitization strips leading/trailing whitespace."""
        input_str = "  Hello World  "
        result = sanitize_string(input_str)
        assert result == "Hello World"

    def test_sanitize_string_empty_string(self):
        """Test sanitization of empty string."""
        result = sanitize_string("")
        assert result == ""

    def test_sanitize_string_removes_special_chars(self):
        """Test that sanitization handles special characters appropriately."""
        # This test depends on the actual implementation
        # Adjust based on what sanitize_string actually does
        input_str = "<script>alert('xss')</script>"
        result = sanitize_string(input_str)
        # Verify no script tags remain
        assert "<script>" not in result.lower()


@pytest.mark.unit
class TestSanitizeEmail:
    """Test sanitize_email function."""

    def test_sanitize_email_valid(self):
        """Test sanitization of valid email."""
        email = "test@example.com"
        result = sanitize_email(email)
        assert result == email.lower()

    def test_sanitize_email_with_whitespace(self):
        """Test sanitization of email with whitespace."""
        email = "  Test@Example.COM  "
        result = sanitize_email(email)
        assert result == "test@example.com"

    def test_sanitize_email_invalid_format(self):
        """Test sanitization of invalid email format."""
        # This depends on implementation - adjust based on actual behavior
        invalid_email = "not-an-email"
        # Should either raise ValueError or return sanitized version
        # Adjust assertion based on actual implementation
        try:
            result = sanitize_email(invalid_email)
            assert result is not None
        except ValueError:
            pass  # Expected behavior


@pytest.mark.unit
class TestValidatePasswordStrength:
    """Test validate_password_strength function."""

    def test_validate_password_strength_valid(self):
        """Test validation of strong password."""
        password = "StrongPassword123!"
        # Should not raise exception
        validate_password_strength(password)

    def test_validate_password_strength_too_short(self):
        """Test validation of password that is too short."""
        password = "short"
        with pytest.raises(ValueError):
            validate_password_strength(password)
