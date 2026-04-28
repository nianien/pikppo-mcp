from pydantic import BaseModel, Field
from uuid import uuid4
from time import time


class RoleCreate(BaseModel):
    name: str
    icon: str = ""
    description: str = ""
    color: int = 0
    system_prompt: str = ""


class RoleUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    description: str | None = None
    color: int | None = None
    system_prompt: str | None = None


class Role(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    icon: str = ""
    description: str = ""
    color: int = 0
    system_prompt: str = ""
    is_default: bool = False
    created_at: int = Field(default_factory=lambda: int(time() * 1000))
