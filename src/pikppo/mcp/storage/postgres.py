import asyncio
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import asyncpg

# 进程级单例：stateless_http 模式下 MCP lifespan 每请求执行一次，
# 池的创建/关闭必须与请求生命周期解耦，否则并发请求会互相关闭共享池
_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()

# 中性持久化框架：当前无任何领域表。需要服务端落库的外部工具在自己的模块里
# 定义表 DDL，并把建表语句追加到此处的 SCHEMA（新表用真实类型 + created_at/updated_at
# 审计列），再重跑 scripts/init-db.py。个人领域数据（日历、笔记等）归客户端本地存储，
# 不在此落库。
SCHEMA = ""


def _dsn() -> str:
    url = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("使用 postgres 后端需要设置 DB_URL 环境变量（可放在 .env）")
    # asyncpg 不识别 channel_binding 参数（Neon 连接串默认携带），需从 DSN 中移除
    parts = urlsplit(url)
    params = [(k, v) for k, v in parse_qsl(parts.query) if k != "channel_binding"]
    return urlunsplit(parts._replace(query=urlencode(params)))


async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await asyncpg.create_pool(_dsn(), min_size=0, max_size=5)
    return _pool


async def init_schema():
    """建表机制（幂等）。仅供 scripts/init-db.py（部署前执行一次）和测试使用，不在请求路径调用。
    SCHEMA 为空时不连库直接返回。"""
    if not SCHEMA.strip():
        return
    pool = await _get_pool()
    await pool.execute(SCHEMA)


async def close():
    """仅供测试 teardown / 初始化脚本使用，不要在请求路径调用"""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
