"""Unit tests for SpeechToText service."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.speech_to_text import SpeechToTextService


@pytest.mark.unit
class TestSpeechToTextService:
    """Test SpeechToTextService."""

    def test_initialization(self):
        service = SpeechToTextService()
        assert service._client is None

    def test_client_lazy_loading(self):
        service = SpeechToTextService()
        with patch("app.services.speech_to_text.speech") as mock_speech:
            mock_speech.SpeechClient.return_value = MagicMock()
            client = service.client
            assert client is not None
            mock_speech.SpeechClient.assert_called_once()

            client2 = service.client
            assert client2 is client
            assert mock_speech.SpeechClient.call_count == 1

    async def test_transcribe_audio_success(self):
        service = SpeechToTextService()

        mock_alternative = MagicMock()
        mock_alternative.transcript = "Hello world"
        mock_result = MagicMock()
        mock_result.alternatives = [mock_alternative]
        mock_response = MagicMock()
        mock_response.results = [mock_result]

        mock_client = MagicMock()
        mock_client.recognize.return_value = mock_response
        service._client = mock_client

        result = await service.transcribe_audio(b"fake audio")

        assert result == "Hello world"
        mock_client.recognize.assert_called_once()

    async def test_transcribe_audio_multiple_results(self):
        service = SpeechToTextService()

        mock_alt1 = MagicMock()
        mock_alt1.transcript = "Hello"
        mock_result1 = MagicMock()
        mock_result1.alternatives = [mock_alt1]

        mock_alt2 = MagicMock()
        mock_alt2.transcript = "World"
        mock_result2 = MagicMock()
        mock_result2.alternatives = [mock_alt2]

        mock_response = MagicMock()
        mock_response.results = [mock_result1, mock_result2]

        mock_client = MagicMock()
        mock_client.recognize.return_value = mock_response
        service._client = mock_client

        result = await service.transcribe_audio(b"fake audio")

        assert result == "Hello World"

    async def test_transcribe_audio_no_results(self):
        service = SpeechToTextService()

        mock_response = MagicMock()
        mock_response.results = []

        mock_client = MagicMock()
        mock_client.recognize.return_value = mock_response
        service._client = mock_client

        result = await service.transcribe_audio(b"silence")

        assert result == ""

    async def test_transcribe_audio_exception(self):
        service = SpeechToTextService()

        mock_client = MagicMock()
        mock_client.recognize.side_effect = Exception("API Error")
        service._client = mock_client

        result = await service.transcribe_audio(b"bad audio")

        assert result is None
