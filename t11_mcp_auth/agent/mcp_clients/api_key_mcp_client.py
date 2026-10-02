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
        self._http_client = httpx2.AsyncClient(headers={"X-API-Key": self.api_key})

        self.client = Client(streamable_http_client(self.mcp_server_url, http_client=self._http_client))
        await self.client.__aenter__()

        print(f"Connected to {self.client.server_info} (protocol version {self.client.protocol_version})")
        print(self.client.server_capabilities.model_dump_json(indent=2, exclude_none=True))

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
            self.client = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def get_tools(self) -> list[dict[str, Any]]:
        """Get available tools from MCP server"""
        if not self.client:
            raise RuntimeError("MCP client not connected. Call connect() first.")

        tools_result = await self.client.list_tools()

        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
            for tool in tools_result.tools
        ]

    async def call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        """Call a specific tool on the MCP server"""
        if not self.client:
            raise RuntimeError("MCP client not connected. Call connect() first.")

        print(f"    🔧 Calling `{tool_name}` with {tool_args}")

        tool_result: CallToolResult = await self.client.call_tool(tool_name, tool_args)
        content = tool_result.content[0]
        print(f"    ⚙️: {content}")

        return content.text if isinstance(content, TextContent) else str(content)