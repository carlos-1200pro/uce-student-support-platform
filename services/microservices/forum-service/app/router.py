from typing import Generic, Optional, TypeVar

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.service import CommentCreate, CommentRead, PostCreate, PostRead, PostUpdate, forum_service

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
    id: str


@router.get(
    "/posts",
    response_model=ApiResponse[list[PostRead]],
    summary="List forum posts",
)
def list_posts():
    return ApiResponse(success=True, data=forum_service.list_posts(), message="ok")


@router.post(
    "/posts",
    response_model=ApiResponse[PostRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create forum post",
)
def create_post(payload: PostCreate):
    data = forum_service.create_post(payload)
    return ApiResponse(success=True, data=data, message="created")


@router.get(
    "/posts/{post_id}",
    response_model=ApiResponse[PostRead],
    summary="Get forum post",
)
def get_post(post_id: str):
    data = forum_service.get_post(post_id)
    return ApiResponse(success=True, data=data, message="ok")


@router.put(
    "/posts/{post_id}",
    response_model=ApiResponse[PostRead],
    summary="Update forum post",
)
def update_post(post_id: str, payload: PostUpdate):
    data = forum_service.update_post(post_id, payload)
    return ApiResponse(success=True, data=data, message="updated")


@router.delete(
    "/posts/{post_id}",
    response_model=ApiResponse[DeleteData],
    summary="Delete forum post",
)
def delete_post(post_id: str):
    deleted = forum_service.delete_post(post_id)
    return ApiResponse(success=True, data=DeleteData(deleted=deleted, id=post_id), message="deleted")


@router.get(
    "/posts/{post_id}/comments",
    response_model=ApiResponse[list[CommentRead]],
    summary="List comments for a post",
)
def list_comments(post_id: str):
    data = forum_service.list_comments(post_id)
    return ApiResponse(success=True, data=data, message="ok")


@router.post(
    "/posts/{post_id}/comments",
    response_model=ApiResponse[CommentRead],
    status_code=status.HTTP_201_CREATED,
    summary="Add comment to a post",
)
def add_comment(post_id: str, payload: CommentCreate):
    data = forum_service.add_comment(post_id, payload)
    return ApiResponse(success=True, data=data, message="created")


@router.get(
    "/info",
    response_model=ApiResponse[InfoData],
    summary="Service info",
)
def info():
    return ApiResponse(
        success=True,
        data=InfoData(
            service="forum-service",
            entity="post",
            endpoints={
                "list": "/api/posts",
                "create": "/api/posts",
                "get": "/api/posts/{post_id}",
                "update": "/api/posts/{post_id}",
                "delete": "/api/posts/{post_id}",
                "comments": "/api/posts/{post_id}/comments",
            },
        ),
        message="info ok",
    )
