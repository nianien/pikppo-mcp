import argparse
import os
import sys

from app.server import mcp

parser = argparse.ArgumentParser()
parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="streamable-http")
parser.add_argument("--host", default="0.0.0.0")
# Cloud Run 等平台通过 $PORT 注入监听端口
parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
args = parser.parse_args()

if args.transport == "stdio":
    mcp.run(transport="stdio")
else:
    import uvicorn

    token = os.environ.get("MCP_AUTH_TOKEN")
    allow_any_host = "*" in os.environ.get("MCP_ALLOWED_HOSTS", "")
    loopback = args.host in ("127.0.0.1", "::1", "localhost")
    if not token:
        # fail-closed：云端形态（Host 白名单已关闭）若 token 缺失（如 secret 挂载失误）即裸奔，拒绝启动
        if allow_any_host:
            sys.exit("拒绝启动：MCP_ALLOWED_HOSTS=* 已关闭 Host 白名单，必须设置 MCP_AUTH_TOKEN")
        if not loopback:
            print(
                f"[警告] 监听 {args.host} 且未设置 MCP_AUTH_TOKEN，局域网内任何设备都可调用本服务",
                file=sys.stderr,
            )

    app = mcp.sse_app() if args.transport == "sse" else mcp.streamable_http_app()
    if token:
        from app.auth import BearerAuthMiddleware

        app = BearerAuthMiddleware(app, token)
    uvicorn.run(app, host=args.host, port=args.port, log_level=mcp.settings.log_level.lower())
