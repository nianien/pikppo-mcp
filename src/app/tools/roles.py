from app.server import mcp
from app.services import role_service
from app.models.role import RoleCreate, RoleUpdate


@mcp.tool()
async def list_roles() -> list[dict]:
    """获取所有角色列表，内置角色排在前面"""
    roles = await role_service.list_roles()
    return [r.model_dump() for r in roles]


@mcp.tool()
async def create_role(
    name: str,
    icon: str = "",
    description: str = "",
    color: int = 0,
    system_prompt: str = "",
) -> dict:
    """创建自定义角色

    Args:
        name: 角色名称
        icon: emoji 图标
        description: 角色描述
        color: 颜色值
        system_prompt: 系统提示词
    """
    role = await role_service.create_role(RoleCreate(
        name=name, icon=icon, description=description,
        color=color, system_prompt=system_prompt,
    ))
    return role.model_dump()


@mcp.tool()
async def update_role(
    role_id: str,
    name: str | None = None,
    icon: str | None = None,
    description: str | None = None,
    color: int | None = None,
    system_prompt: str | None = None,
) -> dict:
    """更新角色信息

    Args:
        role_id: 角色 ID
        name: 角色名称
        icon: emoji 图标
        description: 角色描述
        color: 颜色值
        system_prompt: 系统提示词
    """
    role = await role_service.update_role(role_id, RoleUpdate(
        name=name, icon=icon, description=description,
        color=color, system_prompt=system_prompt,
    ))
    if not role:
        raise ValueError("角色不存在")
    return role.model_dump()


@mcp.tool()
async def delete_role(role_id: str) -> str:
    """删除自定义角色（内置角色无法删除）

    Args:
        role_id: 角色 ID
    """
    ok = await role_service.delete_role(role_id)
    if not ok:
        raise ValueError("角色不存在或为内置角色，无法删除")
    return "已删除"
