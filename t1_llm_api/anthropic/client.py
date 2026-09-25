from anthropic import Anthropic, AsyncAnthropic

from commons.constants import ANTHROPIC_WORKSPACE_ID
from commons.models.message import Message
from commons.models.role import Role
from t1_llm_api.base_client import AIClient


class AnthropicAIClient(AIClient):
    """
    Client for Anthropic's Claude API using the official SDK.

    This implementation uses the official Anthropic Python library to interact
    with Claude models, providing both synchronous and streaming response capabilities.

    Attributes:
        _client (Anthropic): Synchronous Anthropic client instance.
        _async_client (AsyncAnthropic): Asynchronous Anthropic client instance.
        Inherits all other attributes from AIClient.
    """

    def __init__(self, endpoint: str, model_name: str, api_key: str, system_prompt: str):
        """
        Initialize the Anthropic client with SDK.

        Args:
            endpoint (str): The Anthropic API endpoint (for compatibility, not used by SDK).
            model_name (str): The Claude model to use (e.g., 'claude-sonnet-5', 'claude-haiku-4-5').
            api_key (str): The Anthropic API key for authentication.
            system_prompt (str): The system instruction to guide Claude's behavior.
        """
        super().__init__(endpoint=endpoint, model_name=model_name, api_key=api_key, system_prompt=system_prompt)
        # SDK appends "/v1/messages" itself, so it must not be part of base_url
        base_url = endpoint.removesuffix("/v1/messages")
        # Required only for API keys that are not scoped to a workspace
        default_headers = {"anthropic-workspace-id": ANTHROPIC_WORKSPACE_ID} if ANTHROPIC_WORKSPACE_ID else None
        self._client = Anthropic(api_key=api_key, base_url=base_url, default_headers=default_headers)
        self._async_client = AsyncAnthropic(api_key=api_key, base_url=base_url, default_headers=default_headers)

    def response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a synchronous response from Anthropic's Claude API.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters like max_tokens (default: 1024).

        Returns:
            Message: The AI's response message.

        Note:
            Claude's API uses a separate 'system' parameter for system instructions.
            Response content blocks are concatenated into a single text response.
            The response is printed to stdout before being returned.
        """
        kwargs.setdefault("max_tokens", 1024)
        result = self._client.messages.create(
            model=self._model_name,
            system=self._system_prompt,
            messages=[message.to_dict() for message in messages],
            **kwargs
        )
        content = "".join(block.text for block in result.content if block.type == "text")
        print(content)
        return Message(role=Role.ASSISTANT, content=content)

    async def stream_response(self, messages: list[Message], **kwargs) -> Message:
        """
        Get a streaming response from Anthropic's Claude API.

        The response is streamed using event-based streaming, with text deltas
        printed immediately as they arrive.

        Args:
            messages (list[Message]): The conversation history.
            **kwargs: Additional parameters like max_tokens (default: 1024).

        Returns:
            Message: The complete AI response message after all deltas are received.

        Note:
            Listens for 'content_block_delta' events with text deltas.
            Each delta is printed to stdout as it arrives for real-time display.
        """
        kwargs.setdefault("max_tokens", 1024)
        content = ""
        async with self._async_client.messages.stream(
            model=self._model_name,
            system=self._system_prompt,
            messages=[message.to_dict() for message in messages],
            **kwargs
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    content += event.delta.text
                    print(event.delta.text, end="", flush=True)
        print()

        return Message(role=Role.ASSISTANT, content=content)
