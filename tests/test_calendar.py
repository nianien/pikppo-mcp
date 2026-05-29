import pytest

from app.tools.calendar import (
    create_calendar_event,
    delete_calendar_event,
    get_calendar_event,
    list_calendar_events,
    update_calendar_event,
)


async def test_create_and_get_event():
    event = await create_calendar_event(
        title="周会", date="2026-04-23", time="10:00", end_time="11:00", reminder_minutes=15
    )
    fetched = await get_calendar_event(event_id=event["id"])
    assert fetched == event


async def test_list_filters_by_date_range():
    await create_calendar_event(title="A", date="2026-04-01")
    inside = await create_calendar_event(title="B", date="2026-04-15")
    await create_calendar_event(title="C", date="2026-05-01")

    events = await list_calendar_events(start_date="2026-04-10", end_date="2026-04-20")
    assert [e["id"] for e in events] == [inside["id"]]


async def test_list_orders_by_date_then_time():
    a = await create_calendar_event(title="late", date="2026-04-15", time="14:00")
    b = await create_calendar_event(title="early", date="2026-04-15", time="09:00")
    c = await create_calendar_event(title="prev day", date="2026-04-14", time="20:00")

    events = await list_calendar_events()
    assert [e["id"] for e in events] == [c["id"], b["id"], a["id"]]


async def test_update_changes_fields():
    event = await create_calendar_event(title="原标题", date="2026-04-23")
    updated = await update_calendar_event(event_id=event["id"], title="新标题", time="10:00")
    assert updated["title"] == "新标题"
    assert updated["time"] == "10:00"
    assert updated["date"] == "2026-04-23"


async def test_get_missing_event_raises():
    with pytest.raises(ValueError):
        await get_calendar_event(event_id="missing")


async def test_delete_event():
    event = await create_calendar_event(title="临时", date="2026-04-23")
    await delete_calendar_event(event_id=event["id"])
    assert await list_calendar_events() == []

    with pytest.raises(ValueError):
        await delete_calendar_event(event_id=event["id"])
