from typing import Generic, Optional, TypeVar

import os

import jwt
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.service import RecordCreate, RecordRead, RecordUpdate, academic_record_service

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


@router.get(
    "/records",
    response_model=ApiResponse[list[RecordRead]],
    summary="List academic records",
)
def list_records(authorization: str = Header(default="")):
    payload = require_auth(authorization)
    role = payload.get("role")
    email = payload.get("email")
    if role == "student":
        records = academic_record_service.list_records(student_email=email)
    else:
        records = academic_record_service.list_records()
    return ApiResponse(success=True, data=records, message="ok")


@router.post(
    "/records",
    response_model=ApiResponse[RecordRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create academic record",
)
def create_record(payload: RecordCreate, authorization: str = Header(default="")):
    require_role("professor", authorization)
    data = academic_record_service.create_record(payload)
    return ApiResponse(success=True, data=data, message="created")


@router.get(
    "/records/{record_id}",
    response_model=ApiResponse[RecordRead],
    summary="Get academic record",
)
def get_record(record_id: int, authorization: str = Header(default="")):
    payload = require_auth(authorization)
    data = academic_record_service.get_record(record_id)
    if payload.get("role") == "student" and data.student_email != payload.get("email"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
    return ApiResponse(success=True, data=data, message="ok")


@router.put(
    "/records/{record_id}",
    response_model=ApiResponse[RecordRead],
    summary="Update academic record",
)
def update_record(record_id: int, payload: RecordUpdate, authorization: str = Header(default="")):
    require_role("professor", authorization)
    data = academic_record_service.update_record(record_id, payload)
    return ApiResponse(success=True, data=data, message="updated")


@router.delete(
    "/records/{record_id}",
    response_model=ApiResponse[DeleteData],
    summary="Delete academic record",
)
def delete_record(record_id: int, authorization: str = Header(default="")):
    require_role("professor", authorization)
    deleted = academic_record_service.delete_record(record_id)
    return ApiResponse(success=True, data=DeleteData(deleted=deleted, id=record_id), message="deleted")


@router.get(
    "/info",
    response_model=ApiResponse[InfoData],
    summary="Service info",
)
def info():
    return ApiResponse(
        success=True,
        data=InfoData(
            service="academic-record-service",
            entity="record",
            endpoints={
                "list": "/api/records",
                "create": "/api/records",
                "get": "/api/records/{record_id}",
                "update": "/api/records/{record_id}",
                "delete": "/api/records/{record_id}",
            },
        ),
        message="info ok",
    )
