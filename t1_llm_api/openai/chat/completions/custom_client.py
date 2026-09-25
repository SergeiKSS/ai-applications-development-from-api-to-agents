import json
import aiohttp
import requests

from commons.models.message import Message
from commons.models.role import Role
from t1_llm_api.openai.base import BaseOpenAIClient


class CustomOpenAIClient(BaseOpenAIClient):
    """
    Custom HTTP client for OpenAI Chat Completions API.

    This implementation uses raw HTTP requests (requests/aiohttp) instead of
    the official SDK, providing more control over the HTTP layer and demonstrating
    how to interact with the API directly.
    """

    def response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a synchronous response using raw HTTP POST request.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters for the API (currently unused).

        Returns:
            Message: The AI's response message.

        Raises:
            ValueError: If the API response contains no choices.
            Exception: If the HTTP request fails (non-200 status code).

        Note:
            The system prompt is automatically prepended to the messages.
            The response is printed to stdout before being returned.
        """
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }
        full_messages = [Message(role=Role.SYSTEM, content=self._system_prompt), *messages]
        payload = {
            "model": self._model_name,
            "messages": [message.to_dict() for message in full_messages],
            **kwargs,
        }

        http_response = requests.post(url=f"{self._endpoint}/chat/completions", headers=headers, json=payload)
        http_response.raise_for_status()
        data = http_response.json()

        choices = data.get("choices")
        if not choices:
            raise ValueError("API response contains no choices")

        content = choices[0]["message"]["content"]
        print(content)
        return Message(role=Role.ASSISTANT, content=content)

    async def stream_response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a streaming response using raw HTTP with Server-Sent Events (SSE).

        The response is streamed token-by-token using OpenAI's SSE format,
        with each chunk printed immediately as it arrives.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters for the API (currently unused).

        Returns:
            Message: The complete AI response message after all chunks are received.

        Note:
            The system prompt is automatically prepended to the messages.
            Each token is printed to stdout as it arrives.
            Uses Server-Sent Events (SSE) format where each line starts with "data: ".
        """
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }
        full_messages = [Message(role=Role.SYSTEM, content=self._system_prompt), *messages]
        payload = {
            "model": self._model_name,
            "messages": [message.to_dict() for message in full_messages],
            "stream": True,
            **kwargs,
        }

        content = ""
        async with aiohttp.ClientSession() as session:
            async with session.post(url=f"{self._endpoint}/chat/completions", headers=headers, json=payload) as http_response:
                http_response.raise_for_status()
                async for line in http_response.content:
                    line = line.decode("utf-8").strip()
                    if not line.startswith("data: "):
                        continue

                    data = line.removeprefix("data: ")
                    if data == "[DONE]":
                        break

                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content")
                    if delta:
                        content += delta
                        print(delta, end="", flush=True)
        print()

        return Message(role=Role.ASSISTANT, content=content)
