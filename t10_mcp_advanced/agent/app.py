import asyncio

from commons.constants import OPENAI_API_KEY, OPENAI_TERRA_MODEL
from commons.models.message import Message
from commons.models.role import Role
from t10_mcp_advanced.agent.agent import CustomAgentMCP
from t10_mcp_advanced.agent.clients.custom_mcp_client import CustomMCPClient

UMS_MCP_SERVER_URL = "http://localhost:8006/mcp"
DDG_MCP_SERVER_URL = "http://localhost:8010/mcp"

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools for managing users "
    "(search, get, create, update, delete) and for searching the web. "
    "Use the tools whenever they help you answer the user's request."
)


async def main():
    tools = []
    tool_name_client_map = {}

    ums_client = await CustomMCPClient.create(UMS_MCP_SERVER_URL)
    ums_tools = await ums_client.get_tools()
    tools.extend(ums_tools)
    for tool in ums_tools:
        tool_name_client_map[tool["function"]["name"]] = ums_client

    ddg_client = await CustomMCPClient.create(DDG_MCP_SERVER_URL)
    ddg_tools = await ddg_client.get_tools()
    tools.extend(ddg_tools)
    for tool in ddg_tools:
        tool_name_client_map[tool["function"]["name"]] = ddg_client

    try:
        agent = CustomAgentMCP(
            api_key=OPENAI_API_KEY,
            model=OPENAI_TERRA_MODEL,
            tools=tools,
            tool_name_client_map=tool_name_client_map,
        )

        messages = [Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)]

        while True:
            user_input = input("\n> ").strip()
            if user_input.lower() == "exit":
                break
            if not user_input:
                continue

            messages.append(Message(role=Role.USER, content=user_input))
            ai_message = await agent.get_completion(messages)
            messages.append(ai_message)
    finally:
        await ums_client.close()
        await ddg_client.close()



if __name__ == "__main__":
    asyncio.run(main())


# Check if Arkadiy Dobkin present as a user, if not then search info about him in the web and add him