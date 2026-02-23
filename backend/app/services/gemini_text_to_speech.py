"""Text-to-speech service using Google Cloud Gemini API."""

from google.cloud import texttospeech


class GeminiTextToSpeech:
    """Service for synthesizing speech using Google Cloud Text-to-Speech."""

    def __init__(self):
        """Initialize the text-to-speech service."""
        self._client = None
        self._async_client = None

    @property
    def client(self):
        """Lazy-load the text-to-speech client on first access."""
        if self._client is None:
            self._client = texttospeech.TextToSpeechClient()
        return self._client

    @property
    def async_client(self):
        """Lazy-load the async text-to-speech client on first access."""
        if self._async_client is None:
            self._async_client = texttospeech.TextToSpeechAsyncClient()
        return self._async_client


    async def synthesize_async(
        self,
        prompt: str,
        text: str,
        voice_name: str,
        model_name: str = "gemini-2.5-flash-tts",
    ) -> bytes:
        """Asynchronously synthesize speech from the input text and return bytes.
        
        Args:
            prompt: Styling instructions on how to synthesize the content in the text field.
            text: The text to synthesize.
            voice_name: The name of the voice to use for synthesis.
            model_name: The name of the model to use for synthesis. Defaults to "gemini-2.5-flash-tts".

        Returns:
            bytes: The audio content as bytes.
        """
        synthesis_input = texttospeech.SynthesisInput(text=text, prompt=prompt)

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
            model_name=model_name,
        )

        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        response = await self.async_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return response.audio_content
            