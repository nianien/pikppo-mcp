#!/usr/bin/env python3
"""初始化数据库 schema（幂等）。部署前对目标库执行一次：

    python scripts/init-db.py            # 用 .env 的 DB_URL
    DB_URL=postgresql://... python scripts/init-db.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import app  # noqa: F401  # 加载 .env
from app.storage import backend


async def main():
    await backend.init_schema()
    await backend.close()
    print("schema 初始化完成")


asyncio.run(main())
