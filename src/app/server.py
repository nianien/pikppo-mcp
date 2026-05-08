from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from app.database import init_db, close_db


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    await init_db()
    try:
        yield
    finally:
        await close_db()


mcp = FastMCP(
    "pikppo",
    instructions="pikppo 私人管家 MCP 服务，提供角色、日程、记忆、群组、用户配置管理能力",
    lifespan=app_lifespan,
)

# register tools
import app.tools.roles  # noqa: F401, E402
import app.tools.calendar  # noqa: F401, E402
import app.tools.memories  # noqa: F401, E402
import app.tools.groups  # noqa: F401, E402
import app.tools.users  # noqa: F401, E402
