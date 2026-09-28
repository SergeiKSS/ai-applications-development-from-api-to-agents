import base64
import json
import os
from datetime import datetime

import requests

from commons.constants import OPENAI_API_KEY, OPENAI_HOST


class Voice:
    alloy: str = 'alloy'
    ash: str = 'ash'
    ballad: str = 'ballad'
    coral: str = 'coral'
    echo: str = 'echo'
    fable: str = 'fable'
    nova: str = 'nova'
    onyx: str = 'onyx'
    sage: str = 'sage'
    shimmer: str = 'shimmer'


# https://developers.openai.com/api/docs/guides/text-to-speech
# Request:
# curl https://api.openai.com/v1/audio/speech \
#   -H "Authorization: Bearer $OPENAI_API_KEY" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "model": "gpt-4o-mini-tts",
#     "input": "Why can't we say that black is white?",
#     "voice": "coral",
#     "instructions": "Speak in a cheerful and positive tone."
#   }' \
# Response:
#   bytes with audio

#TODO:
# You need to convert text to speech:
#   - Create Client that will go to speech OpenAI API
#   - Call API
#   - Get response and save as .mp3 file
# ---
# Hints:
#   - Use /v1/audio/speech endpoint
#   - Use gpt-4o-mini-tts model


class _OpenAIClient:
    def __init__(self, model_name: str):
        if not OPENAI_API_KEY:
            raise ValueError("API key cannot be null or empty")

        self._api_key = "Bearer " + OPENAI_API_KEY
        self._endpoint = f"{OPENAI_HOST}/openai/deployments/{model_name}/chat/completions"

    def call(self, text: str, voice: str, instructions: str = None, print_response=True):
        headers = {"Authorization": self._api_key, "Content-Type": "application/json"}
        messages = []
        if instructions:
            messages.append({"role": "system", "content": instructions})
        messages.append({"role": "user", "content": text})

        payload = {
            "messages": messages,
            "modalities": ["text", "audio"],
            "audio": {"voice": voice, "format": "mp3"},
        }
        response = requests.post(url=self._endpoint, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            if print_response:
                print(json.dumps(data, indent=2))
            return data

        raise Exception(f"HTTP {response.status_code}: {response.text}")


def save_audio(data: dict) -> str:
    message = data["choices"][0]["message"]
    if "audio" in message:
        audio_bytes = base64.b64decode(message["audio"]["data"])
    else:
        attachment = message["custom_content"]["attachments"][0]
        if "data" in attachment:
            audio_bytes = base64.b64decode(attachment["data"])
        else:
            # DIAL returns generated audio as a file url, not inline base64
            file_response = requests.get(f"{OPENAI_HOST}/v1/{attachment['url']}", headers={"Api-Key": OPENAI_API_KEY})
            file_response.raise_for_status()
            audio_bytes = file_response.content
    filename = os.path.join(os.path.dirname(__file__), f"speech_{datetime.now()}.mp3")
    with open(filename, "wb") as f:
        f.write(audio_bytes)
    print(f"Done, audio saved to {filename}")
    return filename


client = _OpenAIClient(model_name="tts-001")
result = client.call(
    text="Why can't we say that black is white?",
    voice=Voice.coral,
    instructions="Speak in a cheerful and positive tone.",
)
save_audio(result)

