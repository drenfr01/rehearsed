"""Unit tests for Scenario model."""

import pytest

from app.models.scenario import Scenario


@pytest.mark.unit
class TestScenarioModel:
    """Test Scenario model."""

    def test_create_scenario(self):
        scenario = Scenario(
            name="Math Lesson",
            description="A lesson about fractions",
            overview="Students learn fractions",
            system_instructions="Guide the lesson",
            initial_prompt="Hello class!",
            teaching_objectives="Understand fractions",
        )
        assert scenario.name == "Math Lesson"
        assert scenario.description == "A lesson about fractions"
        assert scenario.overview == "Students learn fractions"
        assert scenario.system_instructions == "Guide the lesson"
        assert scenario.initial_prompt == "Hello class!"
        assert scenario.teaching_objectives == "Understand fractions"
        assert scenario.owner_id is None

    def test_user_owned_scenario(self):
        scenario = Scenario(
            name="Custom Scenario",
            description="User's scenario",
            overview="Custom overview",
            system_instructions="Custom instructions",
            initial_prompt="Hi",
            teaching_objectives="Custom objectives",
            owner_id=42,
        )
        assert scenario.owner_id == 42

    def test_global_scenario_default(self):
        scenario = Scenario(
            name="Global",
            description="desc",
            overview="overview",
            system_instructions="instr",
            initial_prompt="prompt",
            teaching_objectives="objectives",
        )
        assert scenario.owner_id is None

    def test_scenario_has_created_at(self):
        scenario = Scenario(
            name="Test",
            description="Test",
            overview="Test",
            system_instructions="Test",
            initial_prompt="Test",
            teaching_objectives="Test",
        )
        assert scenario.created_at is not None
