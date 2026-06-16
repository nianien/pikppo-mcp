import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# 注意：不要给 FastMCP 传 lifespan 管理连接池——stateless_http 模式下 lifespan
# 每请求执行一次，并发请求会互相关闭共享池（storage 层已改为惰性单例自管理）。

# Host header 白名单：覆盖本机、Android 模拟器 (10.0.2.2)、iOS 模拟器/真机常见地址。
# 额外地址可通过环境变量 MCP_ALLOWED_HOSTS="ip1:port,ip2:port" 追加；
# 设为 "*" 则关闭 DNS rebinding 防护（用于 Cloud Run 等反代域名场景，需配合 MCP_AUTH_TOKEN）。
_DEFAULT_ALLOWED_HOSTS = [
    "127.0.0.1", "127.0.0.1:8000",
    "localhost", "localhost:8000",
    "10.0.2.2", "10.0.2.2:8000",
]
_extra_hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
_allow_any_host = "*" in _extra_hosts

mcp = FastMCP(
    "pikppo",
    instructions="pikppo 外部工具 MCP 服务，提供日程等外部能力的工具调用",
    # 无状态模式：会话不落实例内存，Cloud Run 多实例扩容时请求可落任意实例
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=not _allow_any_host,
        allowed_hosts=_DEFAULT_ALLOWED_HOSTS + _extra_hosts,
        allowed_origins=["*"],
    ),
)

# register tools
import app.tools.calendar  # noqa: F401, E402
