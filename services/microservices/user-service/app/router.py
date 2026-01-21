from typing import Generic, Optional, TypeVar

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.service import UserCreate, UserRead, UserUpdate, user_service

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
    entity: str
    endpoints: dict


class DeleteData(BaseModel):
    deleted: bool
    id: int


@router.get(
    "/users",
    response_model=ApiResponse[list[UserRead]],
    summary="List users",
)
def list_users():
    return ApiResponse(success=True, data=user_service.list_users(), message="ok")


@router.post(
    "/users",
    response_model=ApiResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
def create_user(payload: UserCreate):
    data = user_service.create_user(payload)
    return ApiResponse(success=True, data=data, message="created")


@router.get(
    "/users/{user_id}",
    response_model=ApiResponse[UserRead],
    summary="Get user",
)
def get_user(user_id: int):
    data = user_service.get_user(user_id)
    return ApiResponse(success=True, data=data, message="ok")


@router.put(
    "/users/{user_id}",
    response_model=ApiResponse[UserRead],
    summary="Update user",
)
def update_user(user_id: int, payload: UserUpdate):
    data = user_service.update_user(user_id, payload)
    return ApiResponse(success=True, data=data, message="updated")


@router.delete(
    "/users/{user_id}",
    response_model=ApiResponse[DeleteData],
    summary="Delete user",
)
def delete_user(user_id: int):
    deleted = user_service.delete_user(user_id)
    return ApiResponse(success=True, data=DeleteData(deleted=deleted, id=user_id), message="deleted")


@router.get(
    "/info",
    response_model=ApiResponse[InfoData],
    summary="Service info",
)
def info():
    return ApiResponse(
        success=True,
        data=InfoData(
            service="user-service",
            entity="user",
            endpoints={
                "list": "/api/users",
                "create": "/api/users",
                "get": "/api/users/{user_id}",
                "update": "/api/users/{user_id}",
                "delete": "/api/users/{user_id}",
            },
        ),
        message="info ok",
    )
