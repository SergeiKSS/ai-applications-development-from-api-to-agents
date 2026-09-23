from typing import Any, Optional

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, TextContent

from t11_mcp_auth.agent.mcp_clients._base import T11MCPClient
from t11_mcp_auth.agent.mcp_clients._oauth_keycloak import OAuthTokenManager


class OauthHttpMCPClient(T11MCPClient):
    """
    MCP client that authenticates via OAuth 2.0 + PKCE.

    On __aenter__:
      1. Runs the PKCE browser flow (opens Keycloak login once)
      2. Connects to the MCP server with the resulting Bearer token

    On tool calls:
      - Proactively refreshes the token before it expires. MCP is stateless (no session), so the new token
        is simply sent with the next request, there is nothing to reconnect
    """

    def __init__(self, mcp_server_url: str) -> None:
        super().__init__()
        self.mcp_server_url = mcp_server_url
        self.token_manager = OAuthTokenManager()
        self._http_client: Optional[httpx2.AsyncClient] = None

    async def __aenter__(self):
        #TODO:
        # 1. Authenticate via browser PKCE flow using `self.token_manager`
        # 2. Get auth headers from the token manager and create an `httpx2.AsyncClient` with them,
        #    assign to `self._http_client`
        # 3. Create a `Client` from `streamable_http_client` using `self.mcp_server_url` and the http client above,
        #    assign to `self.client`, then enter it (it calls `server/discover`, there is no handshake and no session)
        # 4. Print server info, protocol version and server capabilities
        # 5. Return `self`
        raise NotImplementedError()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        #TODO:
        # 1. If client exists — exit it, passing through the exception info
        # 2. If http client exists — close it (the transport doesn't close an http client that was passed to it)
        raise NotImplementedError()

    async def get_tools(self) -> list[dict[str, Any]]:
        """Get available tools from MCP server"""
        if not self.client:
            raise RuntimeError("MCP client not connected")

        #TODO:
        # 1. Fetch available tools from the client
        # 2. Return them as a list of dicts in the OpenAI function-calling format:
        #    {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
        raise NotImplementedError()

    async def call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.
        Proactively refreshes the token before it expires.
        """
        if not self.client:
            raise RuntimeError("MCP client not connected")

        print(f"    🔧 Calling `{tool_name}` with {tool_args}")

        #TODO:
        # 1. Check if the token is expired via `self.token_manager.is_token_expired()`
        #    If so, print a refresh message and call `self._refresh_token()`
        # 2. Return the result of `await self._do_call_tool(tool_name, tool_args)`
        raise NotImplementedError()

    async def _do_call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        #TODO:
        # 1. Call the tool on the client and assign the result to `tool_result: CallToolResult`
        # 2. If `tool_result.content` is empty — return `"No content returned from tool"`
        # 3. Get the first element, print it with prefix `"    ⚙️: "`, then return its `.text`
        #    if it's a `TextContent`, otherwise return `str(content)`
        raise NotImplementedError()

    async def _refresh_token(self) -> None:
        """Refresh OAuth token and send it with the next requests"""
        #TODO:
        # 1. Refresh the token via `self.token_manager.refresh()`
        # 2. Put the new auth headers into the headers of `self._http_client`. MCP is stateless (no session): every
        #    request is a separate HTTP POST, so the next request uses the new token and there is nothing to reconnect
        # 3. Print "    ✅ Next requests will use the fresh token"
        raise NotImplementedError()
