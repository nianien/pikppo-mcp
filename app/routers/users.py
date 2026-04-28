from fastapi import APIRouter
from app.models.user import UserProfileUpdate
from app.models.response import ApiResponse
from app.services import user_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/profile")
async def get_profile() -> ApiResponse:
    profile = await user_service.get_profile()
    return ApiResponse.ok(profile.model_dump())


@router.put("/profile")
async def update_profile(data: UserProfileUpdate) -> ApiResponse:
    profile = await user_service.update_profile(data)
    return ApiResponse.ok(profile.model_dump())
