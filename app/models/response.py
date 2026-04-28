from typing import Any
from pydantic import BaseModel


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None

    @staticmethod
    def ok(data: Any = None) -> "ApiResponse":
        return ApiResponse(data=data)

    @staticmethod
    def error(code: int, message: str) -> "ApiResponse":
        return ApiResponse(code=code, message=message)
