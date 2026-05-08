from app.server import mcp
from app.services import user_service
from app.models.user import UserProfileUpdate


@mcp.tool()
async def get_user_profile() -> dict:
    """获取用户配置信息"""
    profile = await user_service.get_profile()
    return profile.model_dump()


@mcp.tool()
async def update_user_profile(
    user_name: str | None = None,
    preferred_language: str | None = None,
    current_role_id: str | None = None,
    current_model: str | None = None,
    service_type: str | None = None,
    service_host: str | None = None,
) -> dict:
    """更新用户配置

    Args:
        user_name: 用户名
        preferred_language: 偏好语言
        current_role_id: 当前角色 ID
        current_model: 当前模型名称
        service_type: 服务类型 (ollama / lmstudio)
        service_host: 服务地址
    """
    profile = await user_service.update_profile(UserProfileUpdate(
        user_name=user_name, preferred_language=preferred_language,
        current_role_id=current_role_id, current_model=current_model,
        service_type=service_type, service_host=service_host,
    ))
    return profile.model_dump()
