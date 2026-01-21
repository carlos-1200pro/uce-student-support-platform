from typing import Generic, Optional, TypeVar

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.service import AuditLogCreate, AuditLogRead, AuditLogUpdate, audit_service

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
    "/audits",
    response_model=ApiResponse[list[AuditLogRead]],
    summary="List audit logs",
)
def list_logs():
    return ApiResponse(success=True, data=audit_service.list_logs(), message="ok")


@router.post(
    "/audits",
    response_model=ApiResponse[AuditLogRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create audit log",
)
def create_log(payload: AuditLogCreate):
    data = audit_service.create_log(payload)
    return ApiResponse(success=True, data=data, message="created")


@router.get(
    "/audits/{log_id}",
    response_model=ApiResponse[AuditLogRead],
    summary="Get audit log",
)
def get_log(log_id: int):
    data = audit_service.get_log(log_id)
    return ApiResponse(success=True, data=data, message="ok")


@router.put(
    "/audits/{log_id}",
    response_model=ApiResponse[AuditLogRead],
    summary="Update audit log",
)
def update_log(log_id: int, payload: AuditLogUpdate):
    data = audit_service.update_log(log_id, payload)
    return ApiResponse(success=True, data=data, message="updated")


@router.delete(
    "/audits/{log_id}",
    response_model=ApiResponse[DeleteData],
    summary="Delete audit log",
)
def delete_log(log_id: int):
    deleted = audit_service.delete_log(log_id)
    return ApiResponse(success=True, data=DeleteData(deleted=deleted, id=log_id), message="deleted")


@router.get(
    "/info",
    response_model=ApiResponse[InfoData],
    summary="Service info",
)
def info():
    return ApiResponse(
        success=True,
        data=InfoData(
            service="audit-service",
            entity="audit",
            endpoints={
                "list": "/api/audits",
                "create": "/api/audits",
                "get": "/api/audits/{log_id}",
                "update": "/api/audits/{log_id}",
                "delete": "/api/audits/{log_id}",
            },
        ),
        message="info ok",
    )
