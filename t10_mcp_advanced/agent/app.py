import asyncio
import json
import os

from commons.models.message import Message
from commons.models.role import Role
from t10_mcp_advanced.agent.agent import CustomAgentMCP
from t10_mcp_advanced.agent.clients.custom_mcp_client import CustomMCPClient
from t10_mcp_advanced.agent.clients.mcp_client import MCPClient


async def main():
    #TODO:
    # 1. Take a look what applies CustomAgentMCP
    # 2. Create empty list where you save tools from MCP Servers later
    # 3. Create empty dict where where key is str (tool name) and value is instance of MCPClient or CustomMCPClient
    # 4. Create UMS MCPClient, url is `http://localhost:8006/mcp` (use static method create and don't forget that its async)
    # 5. Collect tools and dict [tool name, mcp client]
    # 6. Do steps 4 and 5 for `http://localhost:8010/mcp` (ddg-mcp-server from docker-compose, provides WEB search tools)
    # 7. Create CustomAgentMCP
    # 8. Create array with Messages and add there System message with simple instructions for LLM that it should help to handle user request
    # 9. Create simple console chat (as we done in previous tasks)
    # 10. When chat is finished, close MCP clients (`close()` method)
    raise NotImplementedError()



if __name__ == "__main__":
    asyncio.run(main())


# Check if Arkadiy Dobkin present as a user, if not then search info about him in the web and add him