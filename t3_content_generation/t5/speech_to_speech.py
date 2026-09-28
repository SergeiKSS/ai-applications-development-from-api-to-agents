import base64
import json
import os
from datetime import datetime

import requests

from commons.constants import OPENAI_API_KEY, OPENAI_HOST, OPENAI_TERRA_MODEL


# https://developers.openai.com/api/docs/guides/audio#add-audio-to-your-existing-application

#TODO:
# You need to generate answer in audio format based on the audio message:
#   - Create Client that is similar with OpenAIClients but extracts from message audio (instead of content)
#   - Call API
#   - Get response as base64 content, decode and save as .mp3 file
# ---
# Hints:
#   - Use /v1/chat/completions endpoint
#   - Use gpt-4o-audio-preview model
#   - Use modalities=["text", "audio"]
#   - Use audio={"voice": "ballad", "format": "mp3"}
#   - Use similar method to encode audio as you have done for images encoding
# ---
# NOTE: `gpt-4o-audio-preview` (single model, audio-in + audio-out) is not available on this proxy.
# Pipeline below chains available deployments instead: transcribe (STT) -> answer (chat) -> synthesize (TTS).


def encode_audio(audio_path: str) -> str:
    with open(audio_path, "rb") as audio_file:
        return base64.b64encode(audio_file.read()).decode("utf-8")


def call_chat(model_name: str, messages: list, print_response=True, **kwargs) -> dict:
    headers = {"Authorization": "Bearer " + OPENAI_API_KEY, "Content-Type": "application/json"}
    endpoint = f"{OPENAI_HOST}/openai/deployments/{model_name}/chat/completions"
    payload = {"messages": messages, **kwargs}
    response = requests.post(url=endpoint, headers=headers, json=payload)

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
    filename = os.path.join(os.path.dirname(__file__), f"answer_{datetime.now()}.mp3")
    with open(filename, "wb") as f:
        f.write(audio_bytes)
    print(f"Done, audio saved to {filename}")
    return filename


audio_file_path = os.path.join(os.path.dirname(__file__), "question.mp3")
encoded_audio = encode_audio(audio_file_path)

transcription = call_chat(
    model_name="gpt-4o-transcribe",
    messages=[{"role": "user", "content": [{"type": "input_audio", "input_audio": {"data": encoded_audio, "format": "mp3"}}]}],
)
question_text = transcription["choices"][0]["message"]["content"]

answer = call_chat(model_name=OPENAI_TERRA_MODEL, messages=[{"role": "user", "content": question_text}])
answer_text = answer["choices"][0]["message"]["content"]

speech = call_chat(
    model_name="tts-001",
    messages=[{"role": "user", "content": answer_text}],
    modalities=["text", "audio"],
    audio={"voice": "ballad", "format": "mp3"},
)
save_audio(speech)


