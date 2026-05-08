from app.server import mcp
from app.services import calendar_service
from app.models.calendar_event import CalendarEventCreate, CalendarEventUpdate


@mcp.tool()
async def list_calendar_events(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """查询日历事件，可按日期范围筛选

    Args:
        start_date: 起始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD
    """
    events = await calendar_service.list_events(start_date, end_date)
    return [e.model_dump() for e in events]


@mcp.tool()
async def get_calendar_event(event_id: str) -> dict:
    """获取单个日历事件详情

    Args:
        event_id: 事件 ID
    """
    event = await calendar_service.get_event(event_id)
    if not event:
        raise ValueError("事件不存在")
    return event.model_dump()


@mcp.tool()
async def create_calendar_event(
    title: str,
    date: str,
    time: str | None = None,
    end_time: str | None = None,
    description: str | None = None,
    reminder_minutes: int | None = None,
) -> dict:
    """创建日历事件

    Args:
        title: 事件标题
        date: 日期 YYYY-MM-DD
        time: 开始时间 HH:mm
        end_time: 结束时间 HH:mm
        description: 事件描述
        reminder_minutes: 提前提醒分钟数
    """
    event = await calendar_service.create_event(CalendarEventCreate(
        title=title, date=date, time=time, end_time=end_time,
        description=description, reminder_minutes=reminder_minutes,
    ))
    return event.model_dump()


@mcp.tool()
async def update_calendar_event(
    event_id: str,
    title: str | None = None,
    date: str | None = None,
    time: str | None = None,
    end_time: str | None = None,
    description: str | None = None,
    reminder_minutes: int | None = None,
) -> dict:
    """更新日历事件

    Args:
        event_id: 事件 ID
        title: 事件标题
        date: 日期 YYYY-MM-DD
        time: 开始时间 HH:mm
        end_time: 结束时间 HH:mm
        description: 事件描述
        reminder_minutes: 提前提醒分钟数
    """
    event = await calendar_service.update_event(event_id, CalendarEventUpdate(
        title=title, date=date, time=time, end_time=end_time,
        description=description, reminder_minutes=reminder_minutes,
    ))
    if not event:
        raise ValueError("事件不存在")
    return event.model_dump()


@mcp.tool()
async def delete_calendar_event(event_id: str) -> str:
    """删除日历事件

    Args:
        event_id: 事件 ID
    """
    ok = await calendar_service.delete_event(event_id)
    if not ok:
        raise ValueError("事件不存在")
    return "已删除"
