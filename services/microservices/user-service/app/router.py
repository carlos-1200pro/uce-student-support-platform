from typing import Generic, Optional, TypeVar

import os

import jwt
from fastapi import APIRouter, Header, HTTPException, status
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


JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def require_auth(authorization: str) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc
    return payload


def require_role(required_role: str, authorization: str) -> dict:
    payload = require_auth(authorization)
    if payload.get("role") != required_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
    return payload


def require_any_role(roles: list[str], authorization: str) -> dict:
    payload = require_auth(authorization)
    if payload.get("role") not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
    return payload


@router.get(
    "/users",
    response_model=ApiResponse[list[UserRead]],
    summary="List users",
)
def list_users(authorization: str = Header(default="")):
    require_role("admin", authorization)
    return ApiResponse(success=True, data=user_service.list_users(), message="ok")


@router.get(
    "/users/students",
    response_model=ApiResponse[list[UserRead]],
    summary="List students",
)
def list_students(authorization: str = Header(default="")):
    require_any_role(["admin", "professor"], authorization)
    return ApiResponse(success=True, data=user_service.list_users(role_filter="student"), message="ok")


@router.get(
    "/users/professors",
    response_model=ApiResponse[list[UserRead]],
    summary="List professors",
)
def list_professors(authorization: str = Header(default="")):
    require_any_role(["admin", "professor"], authorization)
    return ApiResponse(success=True, data=user_service.list_users(role_filter="professor"), message="ok")


@router.post(
    "/users",
    response_model=ApiResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
def create_user(payload: UserCreate, authorization: str = Header(default="")):
    require_role("admin", authorization)
    data = user_service.create_user(payload)
    return ApiResponse(success=True, data=data, message="created")


@router.get(
    "/users/{user_id}",
    response_model=ApiResponse[UserRead],
    summary="Get user",
)
def get_user(user_id: int, authorization: str = Header(default="")):
    require_role("admin", authorization)
    data = user_service.get_user(user_id)
    return ApiResponse(success=True, data=data, message="ok")


@router.put(
    "/users/{user_id}",
    response_model=ApiResponse[UserRead],
    summary="Update user",
)
def update_user(user_id: int, payload: UserUpdate, authorization: str = Header(default="")):
    require_role("admin", authorization)
    data = user_service.update_user(user_id, payload)
    return ApiResponse(success=True, data=data, message="updated")


@router.delete(
    "/users/{user_id}",
    response_model=ApiResponse[DeleteData],
    summary="Delete user",
)
def delete_user(user_id: int, authorization: str = Header(default="")):
    require_role("admin", authorization)
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
