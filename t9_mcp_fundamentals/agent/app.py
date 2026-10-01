import os
import sys
import asyncio
import json
from pathlib import Path

from mcp import Resource
from mcp.types import Prompt

from commons.constants import OPENAI_API_KEY, OPENAI_TERRA_MODEL
from commons.models.message import Message
from commons.models.role import Role
from t9_mcp_fundamentals.agent.agent import AgentMCPFundamentals
from t9_mcp_fundamentals.agent.mcp_clients.stdio import StdioMCPClient
from t9_mcp_fundamentals.agent.prompts import SYSTEM_PROMPT

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STDIO_SERVER_PATH = Path(__file__).resolve().parents[1] / "mcp_server" / "stdio_server.py"


async def main():
    async with StdioMCPClient(
            command=sys.executable,
            args=[str(STDIO_SERVER_PATH)],
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    ) as mcp_client:
        resources: list[Resource] = await mcp_client.get_resources()
        print("Available Resources:")
        for resource in resources:
            print(f"  - {resource.uri}: {resource.description}")

        tools = await mcp_client.get_tools()
        print("Available Tools:")
        print(json.dumps(tools, indent=2))

        agent = AgentMCPFundamentals(
            api_key=OPENAI_API_KEY,
            model=OPENAI_TERRA_MODEL,
            tools=tools,
            mcp_client=mcp_client,
        )

        messages = [Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)]

        prompts: list[Prompt] = await mcp_client.get_prompts()
        print("Available Prompts:")
        for prompt in prompts:
            print(f"  - {prompt.name}: {prompt.description}")

        while True:
            user_input = input("\n> ").strip()
            if user_input.lower() == "exit":
                break
            if not user_input:
                continue

            messages.append(Message(role=Role.USER, content=user_input))
            ai_message = await agent.get_response(messages)
            messages.append(ai_message)


if __name__ == "__main__":
    asyncio.run(main())
