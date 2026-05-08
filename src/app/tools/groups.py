from app.server import mcp
from app.services import group_service
from app.models.group import GroupCreate, GroupUpdate


@mcp.tool()
async def list_groups() -> list[dict]:
    """获取所有群组列表"""
    groups = await group_service.list_groups()
    return [g.model_dump() for g in groups]


@mcp.tool()
async def create_group(name: str, role_ids: list[str] | None = None) -> dict:
    """创建群组

    Args:
        name: 群组名称
        role_ids: 成员角色 ID 列表
    """
    group = await group_service.create_group(GroupCreate(
        name=name, role_ids=role_ids or [],
    ))
    return group.model_dump()


@mcp.tool()
async def update_group(
    group_id: str,
    name: str | None = None,
    role_ids: list[str] | None = None,
) -> dict:
    """更新群组

    Args:
        group_id: 群组 ID
        name: 群组名称
        role_ids: 成员角色 ID 列表
    """
    group = await group_service.update_group(group_id, GroupUpdate(
        name=name, role_ids=role_ids,
    ))
    if not group:
        raise ValueError("群组不存在")
    return group.model_dump()


@mcp.tool()
async def delete_group(group_id: str) -> str:
    """删除群组

    Args:
        group_id: 群组 ID
    """
    ok = await group_service.delete_group(group_id)
    if not ok:
        raise ValueError("群组不存在")
    return "已删除"
