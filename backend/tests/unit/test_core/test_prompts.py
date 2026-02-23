"""Unit tests for prompt templates."""

import pytest

from app.core.prompts.feedback import (
    FEEDBACK_SYSTEM_INSTRUCTIONS_TEMPLATE,
    format_feedback_instructions,
)
from app.core.prompts.pick_answering_student import PICK_ANSWERING_STUDENT_SYSTEM_INSTRUCTIONS
from app.core.prompts.students import (
    APPROPRIATE_RESPONSE_INSTRUCTIONS,
    STUDENT_PROFILES,
    STUDENT_SYSTEM_INSTRUCTIONS_TEMPLATE,
)


@pytest.mark.unit
class TestFormatFeedbackInstructions:
    """Test format_feedback_instructions function."""

    def test_basic_formatting(self):
        result = format_feedback_instructions(
            objective="Evaluate the teacher",
            instructions="Give feedback",
            constraints="Be concise",
            context="Middle school",
        )

        assert "Evaluate the teacher" in result
        assert "Give feedback" in result
        assert "Be concise" in result
        assert "Middle school" in result

    def test_with_output_format(self):
        result = format_feedback_instructions(
            objective="Evaluate",
            instructions="Feedback",
            constraints="Concise",
            context="School",
            output_format="Return as JSON",
        )

        assert "<OUTPUT_FORMAT>" in result
        assert "Return as JSON" in result

    def test_without_output_format(self):
        result = format_feedback_instructions(
            objective="Evaluate",
            instructions="Feedback",
            constraints="Concise",
            context="School",
            output_format="",
        )

        assert "<OUTPUT_FORMAT>" not in result

    def test_xml_tags_present(self):
        result = format_feedback_instructions(
            objective="obj",
            instructions="instr",
            constraints="constr",
            context="ctx",
        )

        assert "<OBJECTIVE_AND_PERSONA>" in result
        assert "</OBJECTIVE_AND_PERSONA>" in result
        assert "<INSTRUCTIONS>" in result
        assert "</INSTRUCTIONS>" in result
        assert "<CONSTRAINTS>" in result
        assert "</CONSTRAINTS>" in result
        assert "<CONTEXT>" in result
        assert "</CONTEXT>" in result

    def test_empty_values(self):
        result = format_feedback_instructions(
            objective="",
            instructions="",
            constraints="",
            context="",
        )
        assert isinstance(result, str)
        assert "<OBJECTIVE_AND_PERSONA>" in result


@pytest.mark.unit
class TestFeedbackTemplate:
    """Test FEEDBACK_SYSTEM_INSTRUCTIONS_TEMPLATE."""

    def test_template_has_placeholders(self):
        assert "{objective}" in FEEDBACK_SYSTEM_INSTRUCTIONS_TEMPLATE
        assert "{instructions}" in FEEDBACK_SYSTEM_INSTRUCTIONS_TEMPLATE
        assert "{constraints}" in FEEDBACK_SYSTEM_INSTRUCTIONS_TEMPLATE
        assert "{context}" in FEEDBACK_SYSTEM_INSTRUCTIONS_TEMPLATE
        assert "{output_format_section}" in FEEDBACK_SYSTEM_INSTRUCTIONS_TEMPLATE


@pytest.mark.unit
class TestStudentPrompts:
    """Test student prompt templates."""

    def test_appropriate_response_instructions_exists(self):
        assert len(APPROPRIATE_RESPONSE_INSTRUCTIONS) > 0
        assert "appropriate" in APPROPRIATE_RESPONSE_INSTRUCTIONS.lower()

    def test_student_profiles_exists(self):
        assert len(STUDENT_PROFILES) > 0
        assert "Student1" in STUDENT_PROFILES or "student" in STUDENT_PROFILES.lower()

    def test_student_system_instructions_template_has_placeholders(self):
        assert "{objective_and_persona}" in STUDENT_SYSTEM_INSTRUCTIONS_TEMPLATE
        assert "{instructions}" in STUDENT_SYSTEM_INSTRUCTIONS_TEMPLATE
        assert "{constraints}" in STUDENT_SYSTEM_INSTRUCTIONS_TEMPLATE
        assert "{context}" in STUDENT_SYSTEM_INSTRUCTIONS_TEMPLATE
        assert "{personality}" in STUDENT_SYSTEM_INSTRUCTIONS_TEMPLATE

    def test_student_template_formatting(self):
        result = STUDENT_SYSTEM_INSTRUCTIONS_TEMPLATE.format(
            objective_and_persona="Be a curious student",
            instructions="Answer questions",
            constraints="Stay in character",
            context="8th grade math",
            personality="Shy but thoughtful",
        )

        assert "Be a curious student" in result
        assert "Answer questions" in result
        assert "Stay in character" in result
        assert "8th grade math" in result
        assert "Shy but thoughtful" in result


@pytest.mark.unit
class TestPickAnsweringStudentPrompt:
    """Test pick answering student prompt template."""

    def test_template_has_placeholders(self):
        assert "{student_profiles}" in PICK_ANSWERING_STUDENT_SYSTEM_INSTRUCTIONS
        assert "{messages}" in PICK_ANSWERING_STUDENT_SYSTEM_INSTRUCTIONS
        assert "{student_number_range}" in PICK_ANSWERING_STUDENT_SYSTEM_INSTRUCTIONS

    def test_template_formatting(self):
        result = PICK_ANSWERING_STUDENT_SYSTEM_INSTRUCTIONS.format(
            student_profiles="Student 1: Alex\nStudent 2: Jordan",
            messages="Teacher: Hello class\n[Alex]: Hi teacher!",
            student_number_range=2,
        )

        assert "Alex" in result
        assert "Jordan" in result
        assert "Hello class" in result
