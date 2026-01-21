from typing import Generic, Optional, TypeVar

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.service import (
    LoginData,
    LoginRequest,
    LogoutData,
    LogoutRequest,
    RegisterData,
    RegisterRequest,
    auth_service,
)

router = APIRouter()

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    message: str


class HealthData(BaseModel):
    status: str
    service: str


class InfoData(BaseModel):
    service: str
    endpoints: dict


@router.post(
    "/register",
    response_model=ApiResponse[RegisterData],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(payload: RegisterRequest):
    data = auth_service.register(payload)
    return ApiResponse(success=True, data=data, message="user registered")


@router.post(
    "/login",
    response_model=ApiResponse[LoginData],
    summary="Login and obtain session token",
)
def login(payload: LoginRequest):
    data = auth_service.login(payload)
    return ApiResponse(success=True, data=data, message="login ok")


@router.post(
    "/logout",
    response_model=ApiResponse[LogoutData],
    summary="Logout and revoke session token",
)
def logout(payload: LogoutRequest):
    data = auth_service.logout(payload)
    return ApiResponse(success=True, data=data, message="logout ok")


@router.get(
    "/info",
    response_model=ApiResponse[InfoData],
    summary="Service info",
)
def info():
    return ApiResponse(
        success=True,
        data=InfoData(
            service="auth-service",
            endpoints={
                "register": "/api/register",
                "login": "/api/login",
                "logout": "/api/logout",
            },
        ),
        message="info ok",
    )
