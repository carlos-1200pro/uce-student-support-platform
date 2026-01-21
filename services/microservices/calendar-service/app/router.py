from typing import Generic, Optional, TypeVar

import os

import jwt
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.service import EventCreate, EventRead, EventUpdate, calendar_service

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


@router.get(
    "/events",
    response_model=ApiResponse[list[EventRead]],
    summary="List calendar events",
)
def list_events(authorization: str = Header(default="")):
    payload = require_auth(authorization)
    role = payload.get("role")
    email = payload.get("email")
    if role == "student":
        events = calendar_service.list_events(student_email=email)
    else:
        events = calendar_service.list_events()
    return ApiResponse(success=True, data=events, message="ok")


@router.post(
    "/events",
    response_model=ApiResponse[EventRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create calendar event",
)
def create_event(payload: EventCreate, authorization: str = Header(default="")):
    payload_auth = require_auth(authorization)
    data = calendar_service.create_event(payload, payload_auth.get("email", "unknown"))
    return ApiResponse(success=True, data=data, message="created")


@router.get(
    "/events/{event_id}",
    response_model=ApiResponse[EventRead],
    summary="Get calendar event",
)
def get_event(event_id: int, authorization: str = Header(default="")):
    payload = require_auth(authorization)
    data = calendar_service.get_event(event_id)
    if payload.get("role") == "student" and data.student_email != payload.get("email"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
    return ApiResponse(success=True, data=data, message="ok")


@router.put(
    "/events/{event_id}",
    response_model=ApiResponse[EventRead],
    summary="Update calendar event",
)
def update_event(event_id: int, payload: EventUpdate, authorization: str = Header(default="")):
    payload_auth = require_auth(authorization)
    event = calendar_service.get_event(event_id)
    if payload_auth.get("role") == "student" and event.student_email != payload_auth.get("email"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
    data = calendar_service.update_event(event_id, payload)
    return ApiResponse(success=True, data=data, message="updated")


@router.delete(
    "/events/{event_id}",
    response_model=ApiResponse[DeleteData],
    summary="Delete calendar event",
)
def delete_event(event_id: int, authorization: str = Header(default="")):
    payload_auth = require_auth(authorization)
    event = calendar_service.get_event(event_id)
    if payload_auth.get("role") == "student" and event.student_email != payload_auth.get("email"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
    deleted = calendar_service.delete_event(event_id)
    return ApiResponse(success=True, data=DeleteData(deleted=deleted, id=event_id), message="deleted")


@router.get(
    "/info",
    response_model=ApiResponse[InfoData],
    summary="Service info",
)
def info():
    return ApiResponse(
        success=True,
        data=InfoData(
            service="calendar-service",
            entity="event",
            endpoints={
                "list": "/api/events",
                "create": "/api/events",
                "get": "/api/events/{event_id}",
                "update": "/api/events/{event_id}",
                "delete": "/api/events/{event_id}",
            },
        ),
        message="info ok",
    )
