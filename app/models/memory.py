from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4
from time import time


class MemoryType(str, Enum):
    semantic = "semantic"
    episodic = "episodic"
    working = "working"


class MemoryCreate(BaseModel):
    type: MemoryType
    content: str
    role_id: str | None = None
    tags: list[str] = []


class MemoryUpdate(BaseModel):
    type: MemoryType | None = None
    content: str | None = None
    role_id: str | None = None
    tags: list[str] | None = None


class Memory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: MemoryType
    content: str
    role_id: str | None = None
    tags: list[str] = []
    timestamp: int = Field(default_factory=lambda: int(time() * 1000))
