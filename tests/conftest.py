import pytest_asyncio

from app import database as db_module


@pytest_asyncio.fixture(autouse=True)
async def isolated_db(tmp_path, monkeypatch):
    # Drop any leftover connection from a previous test/process
    if db_module._db is not None:
        await db_module._db.close()
        db_module._db = None

    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    await db_module.init_db()
    try:
        yield
    finally:
        await db_module.close_db()
