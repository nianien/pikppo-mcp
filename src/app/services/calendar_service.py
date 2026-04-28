from app.database import get_db
from app.models.calendar_event import CalendarEvent, CalendarEventCreate, CalendarEventUpdate


async def list_events(start_date: str | None = None, end_date: str | None = None) -> list[CalendarEvent]:
    db = await get_db()
    query = "SELECT * FROM calendar_events"
    params: list = []
    conditions = []
    if start_date:
        conditions.append("date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("date <= ?")
        params.append(end_date)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY date ASC, time ASC"
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [CalendarEvent(**dict(r)) for r in rows]


async def get_event(event_id: str) -> CalendarEvent | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    return CalendarEvent(**dict(row))


async def create_event(data: CalendarEventCreate) -> CalendarEvent:
    event = CalendarEvent(**data.model_dump())
    db = await get_db()
    await db.execute(
        "INSERT INTO calendar_events (id, title, date, time, end_time, description, reminder_minutes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (event.id, event.title, event.date, event.time, event.end_time, event.description, event.reminder_minutes),
    )
    await db.commit()
    return event


async def update_event(event_id: str, data: CalendarEventUpdate) -> CalendarEvent | None:
    existing = await get_event(event_id)
    if not existing:
        return None
    updates = data.model_dump(exclude_none=True)
    if not updates:
        return existing
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [event_id]
    db = await get_db()
    await db.execute(f"UPDATE calendar_events SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get_event(event_id)


async def delete_event(event_id: str) -> bool:
    db = await get_db()
    cursor = await db.execute("DELETE FROM calendar_events WHERE id = ? RETURNING id", (event_id,))
    row = await cursor.fetchone()
    await db.commit()
    return row is not None