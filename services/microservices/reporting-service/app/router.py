from typing import Generic, Optional, TypeVar

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.service import ReportCreate, ReportRead, ReportUpdate, reporting_service

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
    "/reports",
    response_model=ApiResponse[list[ReportRead]],
    summary="List reports",
)
def list_reports():
    return ApiResponse(success=True, data=reporting_service.list_reports(), message="ok")


@router.post(
    "/reports",
    response_model=ApiResponse[ReportRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create report",
)
def create_report(payload: ReportCreate):
    data = reporting_service.create_report(payload)
    return ApiResponse(success=True, data=data, message="created")


@router.get(
    "/reports/{report_id}",
    response_model=ApiResponse[ReportRead],
    summary="Get report",
)
def get_report(report_id: int):
    data = reporting_service.get_report(report_id)
    return ApiResponse(success=True, data=data, message="ok")


@router.put(
    "/reports/{report_id}",
    response_model=ApiResponse[ReportRead],
    summary="Update report",
)
def update_report(report_id: int, payload: ReportUpdate):
    data = reporting_service.update_report(report_id, payload)
    return ApiResponse(success=True, data=data, message="updated")


@router.delete(
    "/reports/{report_id}",
    response_model=ApiResponse[DeleteData],
    summary="Delete report",
)
def delete_report(report_id: int):
    deleted = reporting_service.delete_report(report_id)
    return ApiResponse(success=True, data=DeleteData(deleted=deleted, id=report_id), message="deleted")


@router.get(
    "/info",
    response_model=ApiResponse[InfoData],
    summary="Service info",
)
def info():
    return ApiResponse(
        success=True,
        data=InfoData(
            service="reporting-service",
            entity="report",
            endpoints={
                "list": "/api/reports",
                "create": "/api/reports",
                "get": "/api/reports/{report_id}",
                "update": "/api/reports/{report_id}",
                "delete": "/api/reports/{report_id}",
            },
        ),
        message="info ok",
    )
