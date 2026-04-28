from pydantic import BaseModel


class UserProfile(BaseModel):
    user_name: str = ""
    preferred_language: str = "zh"
    current_role_id: str | None = None
    current_model: str | None = None
    service_type: str = "ollama"
    service_host: str = "http://localhost:11434"


class UserProfileUpdate(BaseModel):
    user_name: str | None = None
    preferred_language: str | None = None
    current_role_id: str | None = None
    current_model: str | None = None
    service_type: str | None = None
    service_host: str | None = None
