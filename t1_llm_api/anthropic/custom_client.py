import json
import aiohttp
import requests

from commons.constants import ANTHROPIC_WORKSPACE_ID
from commons.models.message import Message
from commons.models.role import Role
from t1_llm_api.base_client import AIClient


class CustomAnthropicAIClient(AIClient):
    """
    Custom HTTP client for Anthropic's Claude API.

    This implementation uses raw HTTP requests (requests/aiohttp) instead of
    the official SDK, demonstrating how to interact with Claude's API directly
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
            ValueError: If the API response contains no content blocks.
            Exception: If the HTTP request fails (non-200 status code).

        Note:
            Requires 'x-api-key' header and 'anthropic-version' header.
            Claude's API returns content as an array of content blocks.
            The response is printed to stdout before being returned.
        """
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        if ANTHROPIC_WORKSPACE_ID:
            headers["anthropic-workspace-id"] = ANTHROPIC_WORKSPACE_ID

        kwargs.setdefault("max_tokens", 1024)
        payload = {
            "model": self._model_name,
            "system": self._system_prompt,
            "messages": [message.to_dict() for message in messages],
            **kwargs,
        }

        http_response = requests.post(url=self._endpoint, headers=headers, json=payload)
        http_response.raise_for_status()
        data = http_response.json()

        content = "".join(block["text"] for block in data.get("content", []) if block.get("type") == "text")
        if not content:
            raise ValueError("API response contains no content blocks")

        print(content)
        return Message(role=Role.ASSISTANT, content=content)

    async def stream_response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a streaming response using raw HTTP with Server-Sent Events (SSE).

        The response is streamed using Anthropic's SSE format, with text deltas
        printed immediately as they arrive.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters like max_tokens (default: 1024).

        Returns:
            Message: The complete AI response message after all deltas are received.

        Note:
            Uses Server-Sent Events (SSE) format where each line starts with "data: ".
            Listens for 'content_block_delta' events with 'text_delta' type.
            Stops processing when 'message_stop' event is received.
            Each delta is printed to stdout as it arrives.
        """
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        if ANTHROPIC_WORKSPACE_ID:
            headers["anthropic-workspace-id"] = ANTHROPIC_WORKSPACE_ID

        kwargs.setdefault("max_tokens", 1024)
        payload = {
            "model": self._model_name,
            "system": self._system_prompt,
            "messages": [message.to_dict() for message in messages],
            "stream": True,
            **kwargs,
        }

        content = ""
        event_type = None
        async with aiohttp.ClientSession() as session:
            async with session.post(url=self._endpoint, headers=headers, json=payload) as http_response:
                http_response.raise_for_status()
                async for line in http_response.content:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue

                    if line.startswith("event: "):
                        event_type = line.removeprefix("event: ")
                        if event_type == "message_stop":
                            break
                        continue

                    if line.startswith("data: ") and event_type == "content_block_delta":
                        chunk = json.loads(line.removeprefix("data: "))
                        delta = chunk.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            content += text
                            print(text, end="", flush=True)
        print()

        return Message(role=Role.ASSISTANT, content=content)

