import json
import aiohttp
import requests

from commons.models.message import Message
from commons.models.role import Role
from t1_llm_api.base_client import AIClient


class CustomGeminiAIClient(AIClient):
    """
    Custom HTTP client for Google Gemini API.

    This implementation uses raw HTTP requests (requests/aiohttp) instead of
    the official SDK, demonstrating how to interact with Gemini's API directly
    and handle its Server-Sent Events (SSE) streaming format.
    """

    def response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a synchronous response using raw HTTP POST request.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters like max_tokens (default: 1024).

        Returns:
            Message: The AI's response message.

        Raises:
            ValueError: If the API response contains no candidates.
            Exception: If the HTTP request fails (non-200 status code).

        Note:
            The URL is constructed by appending ':generateContent' to the model endpoint.
            Uses 'x-goog-api-key' header for authentication.
            Response candidates contain content parts that are concatenated.
        """
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        kwargs.setdefault("maxOutputTokens", 1024)
        payload = {
            "system_instruction": {"parts": [{"text": self._system_prompt}]},
            "contents": [
                {
                    "role": "model" if message.role == Role.ASSISTANT else "user",
                    "parts": [{"text": message.content}],
                }
                for message in messages
            ],
            "generationConfig": kwargs,
        }

        url = f"{self._endpoint}/{self._model_name}:generateContent"
        http_response = requests.post(url=url, headers=headers, json=payload)
        http_response.raise_for_status()
        data = http_response.json()

        candidates = data.get("candidates")
        if not candidates:
            raise ValueError("API response contains no candidates")

        content = "".join(part.get("text", "") for part in candidates[0]["content"]["parts"])
        print(content)
        return Message(role=Role.ASSISTANT, content=content)

    async def stream_response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a streaming response using raw HTTP with Server-Sent Events (SSE).

        The response is streamed using Gemini's SSE format, with text chunks
        printed immediately as they arrive.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters like max_tokens (default: 1024).

        Returns:
            Message: The complete AI response message after all chunks are received.

        Note:
            The URL is constructed with ':streamGenerateContent?alt=sse' endpoint.
            Uses Server-Sent Events (SSE) format where each line starts with "data: ".
            Each SSE chunk contains candidates with content parts.
            Each text chunk is printed to stdout as it arrives.
        """
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        kwargs.setdefault("maxOutputTokens", 1024)
        payload = {
            "system_instruction": {"parts": [{"text": self._system_prompt}]},
            "contents": [
                {
                    "role": "model" if message.role == Role.ASSISTANT else "user",
                    "parts": [{"text": message.content}],
                }
                for message in messages
            ],
            "generationConfig": kwargs,
        }

        url = f"{self._endpoint}/{self._model_name}:streamGenerateContent?alt=sse"
        content = ""
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers, json=payload) as http_response:
                http_response.raise_for_status()
                async for line in http_response.content:
                    line = line.decode("utf-8").strip()
                    if not line.startswith("data: "):
                        continue

                    chunk = json.loads(line.removeprefix("data: "))
                    candidates = chunk.get("candidates")
                    if not candidates:
                        continue

                    for part in candidates[0]["content"]["parts"]:
                        text = part.get("text", "")
                        if text:
                            content += text
                            print(text, end="", flush=True)
        print()

        return Message(role=Role.ASSISTANT, content=content)