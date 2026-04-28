from fastapi import APIRouter, Query
from app.models.memory import MemoryCreate, MemoryUpdate, MemoryType
from app.models.response import ApiResponse
from app.services import memory_service

router = APIRouter(prefix="/api/memories", tags=["memories"])


@router.get("")
async def list_memories(
    type: MemoryType | None = Query(None, description="记忆类型"),
    tags: str | None = Query(None, description="标签，逗号分隔"),
) -> ApiResponse:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    memories = await memory_service.list_memories(type=type, tags=tag_list)
    return ApiResponse.ok([m.model_dump() for m in memories])


@router.post("")
async def create_memory(data: MemoryCreate) -> ApiResponse:
    memory = await memory_service.create_memory(data)
    return ApiResponse.ok(memory.model_dump())


@router.put("/{memory_id}")
async def update_memory(memory_id: str, data: MemoryUpdate) -> ApiResponse:
    memory = await memory_service.update_memory(memory_id, data)
    if not memory:
        return ApiResponse.error(40403, "记忆不存在")
    return ApiResponse.ok(memory.model_dump())


@router.delete("")
async def clear_memories() -> ApiResponse:
    count = await memory_service.clear_memories()
    return ApiResponse.ok({"deleted": count})


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str) -> ApiResponse:
    ok = await memory_service.delete_memory(memory_id)
    if not ok:
        return ApiResponse.error(40403, "记忆不存在")
    return ApiResponse.ok()
