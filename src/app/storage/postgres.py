import asyncio
import datetime
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import asyncpg

from app.models.calendar_event import CalendarEvent, CalendarEventCreate, CalendarEventUpdate

# 进程级单例：stateless_http 模式下 MCP lifespan 每请求执行一次，
# 池的创建/关闭必须与请求生命周期解耦，否则并发请求会互相关闭共享池
_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()

# 模型字段（对外契约：字符串日期/时间）→ PG 列（真实 DATE/TIME 类型；date 是 PG 关键字故列名用 event_date）
_FIELD_TO_COL = {
    "title": "title",
    "date": "event_date",
    "time": "start_time",
    "end_time": "end_time",
    "description": "description",
    "reminder_minutes": "reminder_minutes",
}


def _dsn() -> str:
    url = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("使用 postgres 后端需要设置 DB_URL 环境变量（可放在 .env）")
    # asyncpg 不识别 channel_binding 参数（Neon 连接串默认携带），需从 DSN 中移除
    parts = urlsplit(url)
    params = [(k, v) for k, v in parse_qsl(parts.query) if k != "channel_binding"]
    return urlunsplit(parts._replace(query=urlencode(params)))


def _to_db(field: str, value):
    if value is None:
        return None
    if field == "date":
        return datetime.date.fromisoformat(value)
    if field in ("time", "end_time"):
        return datetime.time.fromisoformat(value)
    return value


def _row_to_event(row: asyncpg.Record) -> CalendarEvent:
    return CalendarEvent(
        id=row["id"],
        title=row["title"],
        date=row["event_date"].isoformat(),
        time=row["start_time"].strftime("%H:%M") if row["start_time"] else None,
        end_time=row["end_time"].strftime("%H:%M") if row["end_time"] else None,
        description=row["description"],
        reminder_minutes=row["reminder_minutes"],
    )


SCHEMA = """
CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    event_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    description TEXT,
    reminder_minutes INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_calendar_events_date ON calendar_events(event_date);
"""


async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await asyncpg.create_pool(_dsn(), min_size=0, max_size=5)
    return _pool


async def init_schema():
    """建表。仅供 scripts/init-db.py（部署前执行一次）和测试 conftest 使用，不在请求路径调用"""
    pool = await _get_pool()
    await pool.execute(SCHEMA)


async def close():
    """仅供测试 teardown / 初始化脚本使用，不要在请求路径调用"""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def list_events(start_date: str | None = None, end_date: str | None = None) -> list[CalendarEvent]:
    query = "SELECT * FROM calendar_events"
    params: list = []
    conditions = []
    if start_date:
        params.append(datetime.date.fromisoformat(start_date))
        conditions.append(f"event_date >= ${len(params)}")
    if end_date:
        params.append(datetime.date.fromisoformat(end_date))
        conditions.append(f"event_date <= ${len(params)}")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    # NULLS FIRST 与 sqlite 的 NULL 排序行为保持一致
    query += " ORDER BY event_date ASC, start_time ASC NULLS FIRST"
    pool = await _get_pool()
    rows = await pool.fetch(query, *params)
    return [_row_to_event(r) for r in rows]


async def get_event(event_id: str) -> CalendarEvent | None:
    pool = await _get_pool()
    row = await pool.fetchrow("SELECT * FROM calendar_events WHERE id = $1", event_id)
    if not row:
        return None
    return _row_to_event(row)


async def create_event(data: CalendarEventCreate) -> CalendarEvent:
    event = CalendarEvent(**data.model_dump())
    pool = await _get_pool()
    await pool.execute(
        "INSERT INTO calendar_events (id, title, event_date, start_time, end_time, description, reminder_minutes) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7)",
        event.id,
        event.title,
        _to_db("date", event.date),
        _to_db("time", event.time),
        _to_db("end_time", event.end_time),
        event.description,
        event.reminder_minutes,
    )
    return event


async def update_event(event_id: str, data: CalendarEventUpdate) -> CalendarEvent | None:
    existing = await get_event(event_id)
    if not existing:
        return None
    updates = data.model_dump(exclude_none=True)
    if not updates:
        return existing
    set_parts = []
    values = []
    for field, value in updates.items():
        values.append(_to_db(field, value))
        set_parts.append(f"{_FIELD_TO_COL[field]} = ${len(values)}")
    set_parts.append("updated_at = NOW()")
    values.append(event_id)
    pool = await _get_pool()
    await pool.execute(
        f"UPDATE calendar_events SET {', '.join(set_parts)} WHERE id = ${len(values)}", *values
    )
    return await get_event(event_id)


async def delete_event(event_id: str) -> bool:
    pool = await _get_pool()
    row = await pool.fetchrow("DELETE FROM calendar_events WHERE id = $1 RETURNING id", event_id)
    return row is not None
