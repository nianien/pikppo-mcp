from pydantic import BaseModel, Field
from uuid import uuid4


class GroupCreate(BaseModel):
    name: str
    role_ids: list[str] = []


class GroupUpdate(BaseModel):
    name: str | None = None
    role_ids: list[str] | None = None


class Group(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    role_ids: list[str] = []
