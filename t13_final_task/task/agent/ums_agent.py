import json
import logging
from collections import defaultdict
from typing import AsyncGenerator

from openai import AsyncOpenAI

from commons.constants import OPENAI_HOST
from t13_final_task.task.agent.models import Message
from t13_final_task.task.agent.models import Role
from t13_final_task.task.agent.guardrail import UMSDataGuardrail
from t13_final_task.task.agent.tools.base import BaseTool

logger = logging.getLogger(__name__)


class UMSAgent:
    """Handles AI model interactions and integrates with MCP client"""

    def __init__(
            self,
            api_key: str,
            model: str,
            tools: list[BaseTool]
    ):
        self.tools: dict[str, BaseTool] = {tool.name: tool for tool in tools}
        self.tools_schemas: list[dict] = [tool.schema for tool in tools]
        self.model = model
        # The SDK appends "/chat/completions" itself, so it must not be part of base_url.
        self.async_openai = AsyncOpenAI(api_key=api_key, base_url=f"{OPENAI_HOST}/openai/deployments/{model}")
        self.guardrail = UMSDataGuardrail()

    async def response(self, messages: list[Message]) -> Message:
        """Non-streaming completion with tool calling support"""
        request_data = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "tools": self.tools_schemas,
            "stream": False,
        }
        if "gpt-5.6" in self.model:
            request_data["reasoning_effort"] = "none"

        completion = await self.async_openai.chat.completions.create(**request_data)
        choice_message = completion.choices[0].message

        ai_message = Message(role=Role.ASSISTANT, content=choice_message.content or "")
        if choice_message.tool_calls:
            ai_message.tool_calls = [tc.model_dump() for tc in choice_message.tool_calls]

        if ai_message.tool_calls:
            messages.append(ai_message)
            await self._call_tools(ai_message, messages)
            return await self.response(messages)

        return ai_message

    async def stream_response(self, messages: list[Message]) -> AsyncGenerator[str, None]:
        """
        Streaming completion with tool calling support.
        Yields SSE-formatted chunks.
        """
        request_data = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "tools": self.tools_schemas,
            "stream": True,
        }
        if "gpt-5.6" in self.model:
            request_data["reasoning_effort"] = "none"

        stream = await self.async_openai.chat.completions.create(**request_data)

        buffered_content = ""
        tool_deltas = []

        async for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.content:
                buffered_content += delta.content
            if delta.tool_calls:
                tool_deltas.extend(delta.tool_calls)

            yield f"data: {json.dumps(chunk.model_dump())}\n\n"

        if tool_deltas:
            tool_calls = self._collect_tool_calls(tool_deltas)
            ai_message = Message(role=Role.ASSISTANT, content=buffered_content, tool_calls=tool_calls)
            messages.append(ai_message)

            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                raw_arguments = tool_call["function"]["arguments"]
                arguments = json.loads(raw_arguments) if raw_arguments else {}

                yield f"data: {json.dumps({'tool_activity': {'type': 'call', 'name': tool_name, 'arguments': arguments}})}\n\n"

                single_call_message = Message(role=Role.ASSISTANT, content="", tool_calls=[tool_call])
                await self._call_tools(single_call_message, messages, silent=True)
                tool_message = messages[-1]

                yield f"data: {json.dumps({'tool_activity': {'type': 'result', 'name': tool_name, 'content': tool_message.content}})}\n\n"

            async for next_chunk in self.stream_response(messages):
                yield next_chunk
            return

        messages.append(Message(role=Role.ASSISTANT, content=buffered_content))

        yield f"data: {json.dumps({'choices': [{'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

    def _collect_tool_calls(self, tool_deltas):
        """Convert streaming tool call deltas to complete tool calls"""
        tool_dict = defaultdict(lambda: {"id": None, "function": {"arguments": "", "name": None}, "type": None})

        for delta in tool_deltas:
            entry = tool_dict[delta.index]
            if delta.id:
                entry["id"] = delta.id
            if delta.type:
                entry["type"] = delta.type
            if delta.function:
                if delta.function.name:
                    entry["function"]["name"] = delta.function.name
                if delta.function.arguments:
                    entry["function"]["arguments"] += delta.function.arguments

        return list(tool_dict.values())

    async def _call_tools(self, ai_message: Message, messages: list[Message], silent: bool = False):
        """Execute tool calls using MCP client"""
        for tool_call in ai_message.tool_calls:
            tool_call_id = tool_call["id"]
            tool_name = tool_call["function"]["name"]
            raw_arguments = tool_call["function"]["arguments"]
            arguments = json.loads(raw_arguments) if raw_arguments else {}

            tool = self.tools.get(tool_name)
            if tool is None:
                messages.append(Message(
                    role=Role.TOOL,
                    tool_call_id=tool_call_id,
                    content=f"ERROR: tool '{tool_name}' not found",
                ))
                continue

            if not silent:
                logger.info("Executing tool call", extra={"tool_name": tool_name, "arguments": arguments})

            tool_message = await tool.execute(tool_call_id, arguments)
            tool_message.content = self.guardrail.redact(tool_message.content)
            messages.append(tool_message)