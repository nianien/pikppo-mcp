from fastapi import APIRouter
from app.models.role import RoleCreate, RoleUpdate
from app.models.response import ApiResponse
from app.services import role_service

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("")
async def list_roles() -> ApiResponse:
    roles = await role_service.list_roles()
    return ApiResponse.ok([r.model_dump() for r in roles])


@router.post("")
async def create_role(data: RoleCreate) -> ApiResponse:
    role = await role_service.create_role(data)
    return ApiResponse.ok(role.model_dump())


@router.put("/{role_id}")
async def update_role(role_id: str, data: RoleUpdate) -> ApiResponse:
    role = await role_service.update_role(role_id, data)
    if not role:
        return ApiResponse.error(40401, "角色不存在")
    return ApiResponse.ok(role.model_dump())


@router.delete("/{role_id}")
async def delete_role(role_id: str) -> ApiResponse:
    ok = await role_service.delete_role(role_id)
    if not ok:
        return ApiResponse.error(40001, "角色不存在或为内置角色，无法删除")
    return ApiResponse.ok()
