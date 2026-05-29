import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.database import init_db, close_db


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    await init_db()
    try:
        yield
    finally:
        await close_db()


# Host header 白名单：覆盖本机、Android 模拟器 (10.0.2.2)、iOS 模拟器/真机常见地址。
# 额外地址可通过环境变量 MCP_ALLOWED_HOSTS="ip1:port,ip2:port" 追加。
_DEFAULT_ALLOWED_HOSTS = [
    "127.0.0.1", "127.0.0.1:8000",
    "localhost", "localhost:8000",
    "10.0.2.2", "10.0.2.2:8000",
]
_extra_hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]

mcp = FastMCP(
    "pikppo",
    instructions="pikppo 私人管家 MCP 服务，提供角色、日程、记忆、群组、用户配置管理能力",
    lifespan=app_lifespan,
    transport_security=TransportSecuritySettings(
        allowed_hosts=_DEFAULT_ALLOWED_HOSTS + _extra_hosts,
        allowed_origins=["*"],
    ),
)

# register tools
import app.tools.roles  # noqa: F401, E402
import app.tools.calendar  # noqa: F401, E402
import app.tools.memories  # noqa: F401, E402
import app.tools.groups  # noqa: F401, E402
import app.tools.users  # noqa: F401, E402
