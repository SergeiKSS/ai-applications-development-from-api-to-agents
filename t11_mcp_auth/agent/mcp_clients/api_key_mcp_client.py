from typing import Any, Optional

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, TextContent

from t11_mcp_auth.agent.mcp_clients._base import T11MCPClient


class ApiKeyMCPClient(T11MCPClient):
    """Handles MCP server connection and tool execution via http"""

    def __init__(self, mcp_server_url: str, api_key: str) -> None:
        super().__init__()
        self.mcp_server_url = mcp_server_url
        self.api_key = api_key
        self._http_client: Optional[httpx2.AsyncClient] = None

    async def __aenter__(self):
        #TODO:
        # 1. Create an `httpx2.AsyncClient` that passes the API key in the `X-API-Key` request header,
        #    assign to `self._http_client`
        # 2. Create a `Client` from `streamable_http_client` using `self.mcp_server_url` and the http client above,
        #    assign to `self.client`, then enter it (it calls `server/discover`, there is no handshake and no session)
        # 3. Print server info, protocol version and server capabilities
        # 4. Return `self`
        raise NotImplementedError()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        #TODO:
        # 1. If client exists — exit it, passing through the exception info
        # 2. If http client exists — close it (the transport doesn't close an http client that was passed to it)
        raise NotImplementedError()

    async def get_tools(self) -> list[dict[str, Any]]:
        """Get available tools from MCP server"""
        if not self.client:
            raise RuntimeError("MCP client not connected. Call connect() first.")

        #TODO:
        # 1. Fetch available tools from the client
        # 2. Return them as a list of dicts in the OpenAI function-calling format, e.g.:
        #    {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
        raise NotImplementedError()

    async def call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        """Call a specific tool on the MCP server"""
        if not self.client:
            raise RuntimeError("MCP client not connected. Call connect() first.")

        print(f"    🔧 Calling `{tool_name}` with {tool_args}")

        #TODO:
        # 1. Call the tool on the client and assign the result to `tool_result: CallToolResult`
        # 2. Get the first element from `tool_result.content` and print it with the prefix `"    ⚙️: "`
        # 3. If the content is a `TextContent` instance — return its `.text`, otherwise return `str(content)`
        raise NotImplementedError()