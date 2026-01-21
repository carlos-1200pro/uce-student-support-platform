from typing import Generic, Optional, TypeVar

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.service import (
    NotificationCreate,
    NotificationRead,
    NotificationUpdate,
    WebhookEventCreate,
    WebhookEventRead,
    notification_service,
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
    entity: str
    endpoints: dict


class DeleteData(BaseModel):
    deleted: bool
    id: int


@router.get(
    "/notifications",
    response_model=ApiResponse[list[NotificationRead]],
    summary="List notifications",
)
def list_notifications():
    return ApiResponse(success=True, data=notification_service.list_notifications(), message="ok")


@router.post(
    "/notifications",
    response_model=ApiResponse[NotificationRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create notification",
)
def create_notification(payload: NotificationCreate):
    data = notification_service.create_notification(payload)
    return ApiResponse(success=True, data=data, message="created")


@router.get(
    "/notifications/{notification_id}",
    response_model=ApiResponse[NotificationRead],
    summary="Get notification",
)
def get_notification(notification_id: int):
    data = notification_service.get_notification(notification_id)
    return ApiResponse(success=True, data=data, message="ok")


@router.put(
    "/notifications/{notification_id}",
    response_model=ApiResponse[NotificationRead],
    summary="Update notification",
)
def update_notification(notification_id: int, payload: NotificationUpdate):
    data = notification_service.update_notification(notification_id, payload)
    return ApiResponse(success=True, data=data, message="updated")


@router.delete(
    "/notifications/{notification_id}",
    response_model=ApiResponse[DeleteData],
    summary="Delete notification",
)
def delete_notification(notification_id: int):
    deleted = notification_service.delete_notification(notification_id)
    return ApiResponse(success=True, data=DeleteData(deleted=deleted, id=notification_id), message="deleted")


@router.get(
    "/webhooks",
    response_model=ApiResponse[list[WebhookEventRead]],
    summary="List webhook events",
)
def list_webhooks():
    return ApiResponse(success=True, data=notification_service.list_webhooks(), message="ok")


@router.post(
    "/webhooks",
    response_model=ApiResponse[WebhookEventRead],
    status_code=status.HTTP_201_CREATED,
    summary="Receive webhook event",
)
def create_webhook(payload: WebhookEventCreate):
    data = notification_service.create_webhook(payload)
    return ApiResponse(success=True, data=data, message="received")


@router.get(
    "/webhooks/{event_id}",
    response_model=ApiResponse[WebhookEventRead],
    summary="Get webhook event",
)
def get_webhook(event_id: int):
    data = notification_service.get_webhook(event_id)
    return ApiResponse(success=True, data=data, message="ok")


@router.get(
    "/info",
    response_model=ApiResponse[InfoData],
    summary="Service info",
)
def info():
    return ApiResponse(
        success=True,
        data=InfoData(
            service="notification-service",
            entity="notification",
            endpoints={
                "list": "/api/notifications",
                "create": "/api/notifications",
                "get": "/api/notifications/{notification_id}",
                "update": "/api/notifications/{notification_id}",
                "delete": "/api/notifications/{notification_id}",
                "webhooks": "/api/webhooks",
                "webhook_get": "/api/webhooks/{event_id}",
            },
        ),
        message="info ok",
    )
