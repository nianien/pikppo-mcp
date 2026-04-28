from fastapi import APIRouter, Query
from app.models.calendar_event import CalendarEventCreate, CalendarEventUpdate
from app.models.response import ApiResponse
from app.services import calendar_service

router = APIRouter(prefix="/api/calendar/events", tags=["calendar"])


@router.get("")
async def list_events(
    start_date: str | None = Query(None, description="起始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
) -> ApiResponse:
    events = await calendar_service.list_events(start_date, end_date)
    return ApiResponse.ok([e.model_dump() for e in events])


@router.get("/{event_id}")
async def get_event(event_id: str) -> ApiResponse:
    event = await calendar_service.get_event(event_id)
    if not event:
        return ApiResponse.error(40402, "事件不存在")
    return ApiResponse.ok(event.model_dump())


@router.post("")
async def create_event(data: CalendarEventCreate) -> ApiResponse:
    event = await calendar_service.create_event(data)
    return ApiResponse.ok(event.model_dump())


@router.put("/{event_id}")
async def update_event(event_id: str, data: CalendarEventUpdate) -> ApiResponse:
    event = await calendar_service.update_event(event_id, data)
    if not event:
        return ApiResponse.error(40402, "事件不存在")
    return ApiResponse.ok(event.model_dump())


@router.delete("/{event_id}")
async def delete_event(event_id: str) -> ApiResponse:
    ok = await calendar_service.delete_event(event_id)
    if not ok:
        return ApiResponse.error(40402, "事件不存在")
    return ApiResponse.ok()
