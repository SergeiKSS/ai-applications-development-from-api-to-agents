import base64
import json
import os

import requests

from commons.constants import OPENAI_API_KEY, OPENAI_HOST


# https://developers.openai.com/api/docs/guides/speech-to-text

#TODO:
# You need to transcribe 'audio_sample.mp3':
#   - Create Client that will go to transcriptions OpenAI API
#   - Call API and provide file (pay attention that you work with 'multipart/form-data')
#   - Get response with transcription
# ---
# Hints:
#   - Use /v1/audio/transcriptions endpoint
#   - Use whisper-1 or gpt-4o-transcribe model


class _OpenAIClient:
    def __init__(self, model_name: str):
        if not OPENAI_API_KEY:
            raise ValueError("API key cannot be null or empty")

        self._api_key = "Bearer " + OPENAI_API_KEY
        self._endpoint = f"{OPENAI_HOST}/openai/deployments/{model_name}/chat/completions"

    def call(self, audio_file_path: str, print_response=True, **kwargs):
        headers = {"Authorization": self._api_key, "Content-Type": "application/json"}
        with open(audio_file_path, "rb") as audio_file:
            encoded_audio = base64.b64encode(audio_file.read()).decode("utf-8")

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Transcribe this audio."},
                        {"type": "input_audio", "input_audio": {"data": encoded_audio, "format": "mp3"}},
                    ],
                }
            ],
            **kwargs,
        }
        response = requests.post(url=self._endpoint, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            if print_response:
                print(json.dumps(data, indent=2))
            return data

        raise Exception(f"HTTP {response.status_code}: {response.text}")


client = _OpenAIClient(model_name="gpt-4o-transcribe")
client.call(
    audio_file_path=os.path.join(os.path.dirname(__file__), "audio_sample.mp3"),
)