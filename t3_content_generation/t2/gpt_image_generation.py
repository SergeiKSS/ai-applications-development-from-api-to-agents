import os
from datetime import datetime

import requests

from commons.constants import OPENAI_API_KEY, OPENAI_HOST
from t3_content_generation._openai_client import OpenAIClientT3


# https://developers.openai.com/api/reference/resources/images/methods/generate
# ---
# Request:
# curl -X POST "https://api.openai.com/v1/images/generations" \
#     -H "Authorization: Bearer $OPENAI_API_KEY" \
#     -H "Content-type: application/json" \
#     -d '{
#         "model": "gpt-image-2",
#         "prompt": "smiling catdog."
#     }'
# Response:
# {
#   "created": 1699900000,
#   "data": [
#     {
#       "b64_json": Qt0n6ArYAEABGOhEoYgVAJFdt8jM79uW2DO...,
#     }
#   ]
# }

#TODO:
# You need to create some images with `gpt-image-2` model:
#   - Generate an image with 'Smiling catdog'
#   - Decode and save it locally
# ---
# Hints:
#   - Use OpenAIClientT3 to connect to OpenAI API
#   - Use /v1/images/generations endpoint
#   - The image will be returned in base64 format


def main(model_name: str, request: str):
    client = OpenAIClientT3(f"{OPENAI_HOST}/openai/deployments/{model_name}/chat/completions")
    response = client.call(messages=[{"role": "user", "content": request}])
    attachment = response["choices"][0]["message"]["custom_content"]["attachments"][0]
    # this deployment returns generated images as a DIAL file url, not inline base64
    file_response = requests.get(f"{OPENAI_HOST}/v1/{attachment['url']}", headers={"Api-Key": OPENAI_API_KEY})
    file_response.raise_for_status()
    image_bytes = file_response.content
    filename = os.path.join(os.path.dirname(__file__), f"{datetime.now()}.png")
    with open(filename, "wb") as f:
        f.write(image_bytes)
    print(f"Done, image saved to {filename}")


main(
    model_name="gpt-image-2-2026-04-21",
    request="Smiling catdog",
)
