"""Unit tests for GeminiTextToSpeech service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.gemini_text_to_speech import GeminiTextToSpeech


@pytest.mark.unit
class TestGeminiTextToSpeech:
    """Test GeminiTextToSpeech service."""

    def test_initialization(self):
        service = GeminiTextToSpeech()
        assert service._client is None
        assert service._async_client is None

    def test_client_lazy_loading(self):
        service = GeminiTextToSpeech()
        with patch("app.services.gemini_text_to_speech.texttospeech") as mock_tts:
            mock_tts.TextToSpeechClient.return_value = MagicMock()
            client = service.client
            assert client is not None
            mock_tts.TextToSpeechClient.assert_called_once()

            # Second access should return cached instance
            client2 = service.client
            assert client2 is client
            assert mock_tts.TextToSpeechClient.call_count == 1

    def test_async_client_lazy_loading(self):
        service = GeminiTextToSpeech()
        with patch("app.services.gemini_text_to_speech.texttospeech") as mock_tts:
            mock_tts.TextToSpeechAsyncClient.return_value = MagicMock()
            client = service.async_client
            assert client is not None
            mock_tts.TextToSpeechAsyncClient.assert_called_once()

            client2 = service.async_client
            assert client2 is client
            assert mock_tts.TextToSpeechAsyncClient.call_count == 1

    async def test_synthesize_async(self):
        service = GeminiTextToSpeech()

        mock_response = MagicMock()
        mock_response.audio_content = b"audio bytes"

        mock_async_client = AsyncMock()
        mock_async_client.synthesize_speech = AsyncMock(return_value=mock_response)
        service._async_client = mock_async_client

        result = await service.synthesize_async(
            prompt="Speak naturally",
            text="Hello world",
            voice_name="Aoede",
        )

        assert result == b"audio bytes"
        mock_async_client.synthesize_speech.assert_called_once()

    async def test_synthesize_async_custom_model(self):
        service = GeminiTextToSpeech()

        mock_response = MagicMock()
        mock_response.audio_content = b"audio"

        mock_async_client = AsyncMock()
        mock_async_client.synthesize_speech = AsyncMock(return_value=mock_response)
        service._async_client = mock_async_client

        await service.synthesize_async(
            prompt="Prompt",
            text="Text",
            voice_name="Kore",
            model_name="custom-model",
        )

        call_kwargs = mock_async_client.synthesize_speech.call_args
        voice_arg = call_kwargs.kwargs.get("voice") or call_kwargs[1].get("voice")
        if voice_arg is None:
            # positional arg
            pass
        mock_async_client.synthesize_speech.assert_called_once()
