from fastapi import APIRouter
from app.models.group import GroupCreate, GroupUpdate
from app.models.response import ApiResponse
from app.services import group_service

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("")
async def list_groups() -> ApiResponse:
    groups = await group_service.list_groups()
    return ApiResponse.ok([g.model_dump() for g in groups])


@router.post("")
async def create_group(data: GroupCreate) -> ApiResponse:
    group = await group_service.create_group(data)
    return ApiResponse.ok(group.model_dump())


@router.put("/{group_id}")
async def update_group(group_id: str, data: GroupUpdate) -> ApiResponse:
    group = await group_service.update_group(group_id, data)
    if not group:
        return ApiResponse.error(40404, "群组不存在")
    return ApiResponse.ok(group.model_dump())


@router.delete("/{group_id}")
async def delete_group(group_id: str) -> ApiResponse:
    ok = await group_service.delete_group(group_id)
    if not ok:
        return ApiResponse.error(40404, "群组不存在")
    return ApiResponse.ok()
