import os
from google.cloud import texttospeech
from app.core.config import settings

class GeminiTextToSpeech:
    def __init__(self):
        self.client = texttospeech.TextToSpeechClient()

    def synthesize(self, prompt: str, text: str, voice_name: str, model_name: str = "gemini-2.5-flash-tts") -> bytes:
        """Synthesizes speech from the input text and returnss the audio content as bytes.
            Note: we deliberately avoid saving the audio content to a file in this function.

        Args:
            prompt: Styling instructions on how to synthesize the content in
            the text field.
            text: The text to synthesize.
            output_filepath: The path to save the generated audio file.
            Defaults to "output.mp3".
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
            