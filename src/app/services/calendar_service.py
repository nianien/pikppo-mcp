from app.storage import backend
from app.models.calendar_event import CalendarEvent, CalendarEventCreate, CalendarEventUpdate


async def list_events(start_date: str | None = None, end_date: str | None = None) -> list[CalendarEvent]:
    return await backend.list_events(start_date, end_date)


async def get_event(event_id: str) -> CalendarEvent | None:
    return await backend.get_event(event_id)


async def create_event(data: CalendarEventCreate) -> CalendarEvent:
    return await backend.create_event(data)


async def update_event(event_id: str, data: CalendarEventUpdate) -> CalendarEvent | None:
    return await backend.update_event(event_id, data)


async def delete_event(event_id: str) -> bool:
    return await backend.delete_event(event_id)
