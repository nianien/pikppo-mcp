import os
import re

import pytest
import pytest_asyncio

import app  # noqa: F401  # 加载 .env
from app.storage import backend


def _test_dsn() -> str:
    url = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.exit("缺少 DB_URL，无法运行数据库测试", returncode=1)
    # 同一 Neon 实例下的独立测试库，避免污染真实数据
    test_url = re.sub(r"(://[^/]+/)[^?]+", r"\g<1>pikppo_test", url)
    # 重写失败就中止：绝不能让 TRUNCATE 落到真实库上
    if test_url == url or "/pikppo_test" not in test_url:
        pytest.exit(f"DSN 重写为测试库失败，拒绝运行（原始 host/path 结构不符合预期）", returncode=1)
    return test_url


@pytest_asyncio.fixture(scope="session", autouse=True)
async def pg_backend():
    os.environ["DB_URL"] = _test_dsn()
    await backend.init_schema()
    try:
        yield
    finally:
        await backend.close()


@pytest_asyncio.fixture(autouse=True)
async def clean_table(pg_backend):
    await backend._pool.execute("TRUNCATE calendar_events")
