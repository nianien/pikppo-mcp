from pydantic import BaseModel, Field
from uuid import uuid4


class CalendarEventCreate(BaseModel):
    title: str
    date: str  # YYYY-MM-DD
    time: str | None = None  # HH:mm
    end_time: str | None = None
    description: str | None = None
    reminder_minutes: int | None = None


class CalendarEventUpdate(BaseModel):
    title: str | None = None
    date: str | None = None
    time: str | None = None
    end_time: str | None = None
    description: str | None = None
    reminder_minutes: int | None = None


class CalendarEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    date: str
    time: str | None = None
    end_time: str | None = None
    description: str | None = None
    reminder_minutes: int | None = None
