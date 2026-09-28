import base64
import os
from datetime import datetime

import requests

from commons.constants import OPENAI_API_KEY, OPENAI_HOST
from t3_content_generation._openai_client import OpenAIClientT3


# https://developers.openai.com/api/reference/resources/images/methods/edit
# ---
# Request (multipart/form-data, NOT json):
# curl -X POST "https://api.openai.com/v1/images/edits" \
#     -H "Authorization: Bearer $OPENAI_API_KEY" \
#     -F "model=gpt-image-1" \
#     -F "image=@logo.png" \
#     -F "prompt=Add magical sparkles and glowing aura around the logo"
# Response:
# {
#   "created": 1699900000,
#   "data": [
#     {
#       "b64_json": "Qt0n6ArYAEABGOhEoYgVAJFdt8jM79uW2DO..."
#     }
#   ]
# }

#TODO:
# You need to edit an existing image with `gpt-image-2` model:
#   - Take a local image (e.g. 'logo.png') and a prompt describing the edit
#   - Send it to the OpenAI images edit API
#   - Decode the returned base64 image and save it locally
# ---
# Hints:
#   - Use /v1/images/edits endpoint
#   - The request must be 'multipart/form-data' (NOT json) — pass the image as a file and the prompt/model as form fields
#   - The edited image will be returned in base64 format


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def main(model_name: str, image_path: str, prompt: str, **kwargs):
    client = OpenAIClientT3(f"{OPENAI_HOST}/openai/deployments/{model_name}/chat/completions")
    encoded_image = encode_image(image_path)
    response = client.call(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}},
                ],
            }
        ],
        **kwargs,
    )
    attachment = response["choices"][0]["message"]["custom_content"]["attachments"][0]
    file_response = requests.get(f"{OPENAI_HOST}/v1/{attachment['url']}", headers={"Api-Key": OPENAI_API_KEY})
    file_response.raise_for_status()
    image_bytes = file_response.content
    filename = os.path.join(os.path.dirname(__file__), f"edited_{datetime.now()}.png")
    with open(filename, "wb") as f:
        f.write(image_bytes)
    print(f"Done, image saved to {filename}")


main(
    model_name="gpt-image-2-2026-04-21",
    image_path=os.path.join(os.path.dirname(__file__), "logo.png"),
    prompt="Add magical sparkles and a glowing aura around the logo, keep the text readable",
)