"""Integration tests for Gemini Live API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.graph import SummaryFeedbackResponse


@pytest.mark.integration
@pytest.mark.asyncio
class TestSummaryFeedbackEndpoint:
    """Test POST /api/v1/gemini-live/summary-feedback endpoint."""

    @pytest.fixture
    def mock_summary_response(self):
        return SummaryFeedbackResponse(
            lesson_summary="The lesson covered fractions.",
            key_moments="Good questioning technique",
            overall_feedback="Well done overall",
            your_strengths="Clear explanations",
            areas_for_growth="More examples needed",
            next_steps="Try open-ended questions",
            celebration="Great engagement!",
        )

    async def test_summary_feedback_success(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_scenario,
        mock_summary_response,
    ):
        """Test successful summary feedback generation."""
        with patch(
            "app.api.v1.gemini_live.generate_summary_feedback",
            new_callable=AsyncMock,
            return_value=mock_summary_response,
        ):
            response = await async_client.post(
                "/api/v1/gemini-live/summary-feedback",
                headers=authenticated_headers,
                json={
                    "scenario_id": test_scenario.id,
                    "transcript": [
                        {"role": "user", "text": "Hello class!"},
                        {"role": "agent", "text": "Hi teacher!"},
                    ],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "summary_feedback" in data
            feedback = data["summary_feedback"]
            assert feedback["lesson_summary"] == "The lesson covered fractions."
            assert feedback["key_moments"] == "Good questioning technique"

    async def test_summary_feedback_fallback_string(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_scenario,
    ):
        """Test summary feedback when service returns fallback string."""
        with patch(
            "app.api.v1.gemini_live.generate_summary_feedback",
            new_callable=AsyncMock,
            return_value="No summary feedback configured for this scenario.",
        ):
            response = await async_client.post(
                "/api/v1/gemini-live/summary-feedback",
                headers=authenticated_headers,
                json={
                    "scenario_id": test_scenario.id,
                    "transcript": [
                        {"role": "user", "text": "Hello!"},
                    ],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["summary_feedback"] == "No summary feedback configured for this scenario."

    async def test_summary_feedback_unauthorized(
        self,
        async_client: AsyncClient,
    ):
        """Test summary feedback without authentication."""
        response = await async_client.post(
            "/api/v1/gemini-live/summary-feedback",
            json={
                "scenario_id": 1,
                "transcript": [
                    {"role": "user", "text": "Hello!"},
                ],
            },
        )
        assert response.status_code == 401

    async def test_summary_feedback_empty_transcript(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
        test_scenario,
        mock_summary_response,
    ):
        """Test summary feedback with empty transcript."""
        with patch(
            "app.api.v1.gemini_live.generate_summary_feedback",
            new_callable=AsyncMock,
            return_value=mock_summary_response,
        ):
            response = await async_client.post(
                "/api/v1/gemini-live/summary-feedback",
                headers=authenticated_headers,
                json={
                    "scenario_id": test_scenario.id,
                    "transcript": [],
                },
            )

            assert response.status_code == 200

    async def test_summary_feedback_invalid_request_body(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
    ):
        """Test summary feedback with missing required fields."""
        response = await async_client.post(
            "/api/v1/gemini-live/summary-feedback",
            headers=authenticated_headers,
            json={},
        )
        assert response.status_code == 422

    async def test_summary_feedback_missing_scenario_id(
        self,
        async_client: AsyncClient,
        authenticated_headers: dict,
    ):
        """Test summary feedback with missing scenario_id."""
        response = await async_client.post(
            "/api/v1/gemini-live/summary-feedback",
            headers=authenticated_headers,
            json={
                "transcript": [{"role": "user", "text": "Hello"}],
            },
        )
        assert response.status_code == 422
