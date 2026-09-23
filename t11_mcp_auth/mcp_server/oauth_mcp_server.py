import uvicorn

from t11_mcp_auth.mcp_server._server import mcp
from t11_mcp_auth.mcp_server.auth.oauth import JWTAuthMiddleware

#TODO:
# 1. Create the stateless Starlette app by calling `mcp.http_app(stateless_http=True)` and assign to `app`
#    (no sessions: every request is authenticated and processed on its own)
# 2. Add `JWTAuthMiddleware` to the app
raise NotImplementedError()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8008,
        log_level="info"
    )