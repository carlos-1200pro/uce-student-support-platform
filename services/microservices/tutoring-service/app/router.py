from typing import Generic, Optional, TypeVar

import os

import jwt
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.service import TicketRead, TutoringCreate, TutoringRead, TutoringUpdate, tutoring_service

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


class ReserveData(BaseModel):
    session_id: int
    student: str


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
    "/tutorings",
    response_model=ApiResponse[list[TutoringRead]],
    summary="List tutoring sessions",
)
def list_sessions(authorization: str = Header(default="")):
    payload = require_auth(authorization)
    role = payload.get("role")
    email = payload.get("email")
    if role == "professor":
        sessions = tutoring_service.list_sessions(teacher_email=email)
    else:
        sessions = tutoring_service.list_sessions()
    return ApiResponse(success=True, data=sessions, message="ok")


@router.post(
    "/tutorings",
    response_model=ApiResponse[TutoringRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create tutoring session",
)
def create_session(payload: TutoringCreate, authorization: str = Header(default="")):
    auth_payload = require_role("professor", authorization)
    data = tutoring_service.create_session(payload, auth_payload.get("email", ""))
    return ApiResponse(success=True, data=data, message="created")


@router.get(
    "/tutorings/{session_id}",
    response_model=ApiResponse[TutoringRead],
    summary="Get tutoring session",
)
def get_session(session_id: int):
    data = tutoring_service.get_session(session_id)
    return ApiResponse(success=True, data=data, message="ok")


@router.put(
    "/tutorings/{session_id}",
    response_model=ApiResponse[TutoringRead],
    summary="Update tutoring session",
)
def update_session(session_id: int, payload: TutoringUpdate, authorization: str = Header(default="")):
    require_role("professor", authorization)
    data = tutoring_service.update_session(session_id, payload)
    return ApiResponse(success=True, data=data, message="updated")


@router.post(
    "/tutorings/{session_id}/reserve",
    response_model=ApiResponse[ReserveData],
    summary="Reserve tutoring session",
)
def reserve_session(session_id: int, authorization: str = Header(default="")):
    payload = require_role("student", authorization)
    session = tutoring_service.reserve_session(session_id, payload.get("email", "student"))
    return ApiResponse(
        success=True,
        data=ReserveData(session_id=session.id, student=session.student),
        message="reserved",
    )


@router.delete(
    "/tutorings/{session_id}",
    response_model=ApiResponse[DeleteData],
    summary="Delete tutoring session",
)
def delete_session(session_id: int):
    deleted = tutoring_service.delete_session(session_id)
    return ApiResponse(success=True, data=DeleteData(deleted=deleted, id=session_id), message="deleted")


@router.get(
    "/tickets",
    response_model=ApiResponse[list[TicketRead]],
    summary="List tutoring tickets",
)
def list_tickets(authorization: str = Header(default="")):
    payload = require_auth(authorization)
    role = payload.get("role")
    email = payload.get("email")
    if role == "student":
        tickets = tutoring_service.list_tickets(student_email=email)
    elif role == "professor":
        tickets = tutoring_service.list_tickets(teacher_email=email)
    else:
        tickets = tutoring_service.list_tickets()
    return ApiResponse(success=True, data=tickets, message="ok")


@router.get(
    "/tickets/{ticket_id}",
    response_model=ApiResponse[TicketRead],
    summary="Get tutoring ticket",
)
def get_ticket(ticket_id: int, authorization: str = Header(default="")):
    payload = require_auth(authorization)
    data = tutoring_service.get_ticket(ticket_id)
    if payload.get("role") == "student" and data.student != payload.get("email"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
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
            service="tutoring-service",
            entity="tutoring",
            endpoints={
                "list": "/api/tutorings",
                "create": "/api/tutorings",
                "get": "/api/tutorings/{session_id}",
                "update": "/api/tutorings/{session_id}",
                "delete": "/api/tutorings/{session_id}",
                "reserve": "/api/tutorings/{session_id}/reserve",
                "tickets": "/api/tickets",
                "ticket_get": "/api/tickets/{ticket_id}",
            },
        ),
        message="info ok",
    )
