"""Text-to-speech service using Google Cloud Gemini API."""

from google.cloud import texttospeech

class GeminiTextToSpeech:
    """Service for synthesizing speech using Google Cloud Text-to-Speech."""

    def __init__(self):
        """Initialize the text-to-speech client."""
        self.client = texttospeech.TextToSpeechClient()

    def synthesize(self, prompt: str, text: str, voice_name: str, model_name: str = "gemini-2.5-flash-tts") -> bytes:
        """Synthesize speech from the input text and return the audio content as bytes.

        Note: we deliberately avoid saving the audio content to a file in this function.

        Args:
            prompt: Styling instructions on how to synthesize the content in the text field.
            text: The text to synthesize.
            voice_name: The name of the voice to use for synthesis.
            model_name: The name of the model to use for synthesis. Defaults to "gemini-2.5-flash-tts".

        Returns:
            bytes: The audio content as bytes.
        """
        synthesis_input = texttospeech.SynthesisInput(text=text, prompt=prompt)

        # Select the voice you want to use.
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
            model_name=model_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        # Perform the text-to-speech request on the text input with the selected
        # voice parameters and audio file type.
        response = self.client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # The response's audio_content is binary.
        return response.audio_content
            