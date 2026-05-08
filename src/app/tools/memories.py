from app.server import mcp
from app.services import memory_service
from app.models.memory import MemoryCreate, MemoryUpdate, MemoryType


@mcp.tool()
async def list_memories(
    type: str | None = None,
    tags: list[str] | None = None,
) -> list[dict]:
    """查询记忆，可按类型和标签筛选

    Args:
        type: 记忆类型 (semantic=语义记忆 / episodic=情景记忆 / working=工作记忆)
        tags: 标签列表，筛选包含这些标签的记忆
    """
    memory_type = MemoryType(type) if type else None
    memories = await memory_service.list_memories(type=memory_type, tags=tags)
    return [m.model_dump() for m in memories]


@mcp.tool()
async def create_memory(
    type: str,
    content: str,
    role_id: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """创建一条记忆

    Args:
        type: 记忆类型 (semantic / episodic / working)
        content: 记忆内容
        role_id: 关联角色 ID
        tags: 标签列表
    """
    memory = await memory_service.create_memory(MemoryCreate(
        type=MemoryType(type), content=content,
        role_id=role_id, tags=tags or [],
    ))
    return memory.model_dump()


@mcp.tool()
async def update_memory(
    memory_id: str,
    type: str | None = None,
    content: str | None = None,
    role_id: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """更新一条记忆

    Args:
        memory_id: 记忆 ID
        type: 记忆类型 (semantic / episodic / working)
        content: 记忆内容
        role_id: 关联角色 ID
        tags: 标签列表
    """
    memory = await memory_service.update_memory(memory_id, MemoryUpdate(
        type=MemoryType(type) if type else None,
        content=content, role_id=role_id, tags=tags,
    ))
    if not memory:
        raise ValueError("记忆不存在")
    return memory.model_dump()


@mcp.tool()
async def delete_memory(memory_id: str) -> str:
    """删除单条记忆

    Args:
        memory_id: 记忆 ID
    """
    ok = await memory_service.delete_memory(memory_id)
    if not ok:
        raise ValueError("记忆不存在")
    return "已删除"


@mcp.tool()
async def clear_memories() -> str:
    """清空所有记忆"""
    count = await memory_service.clear_memories()
    return f"已清空 {count} 条记忆"
