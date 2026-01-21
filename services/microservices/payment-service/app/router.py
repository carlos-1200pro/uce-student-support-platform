from typing import Generic, Optional, TypeVar

import os

import jwt
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.service import (
    FeeCreate,
    FeeRead,
    FeeUpdate,
    OrderCreate,
    OrderRead,
    PayRequest,
    ReceiptRead,
    PaymentCreate,
    PaymentRead,
    PaymentUpdate,
    PaypalOrderRequest,
    PaypalOrderResponse,
    payment_service,
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
    "/payments",
    response_model=ApiResponse[list[PaymentRead]],
    summary="List payments",
)
def list_payments(authorization: str = Header(default="")):
    payload = require_auth(authorization)
    role = payload.get("role")
    email = payload.get("email")
    if role == "student":
        payments = payment_service.list_payments(student_email=email)
    else:
        payments = payment_service.list_payments()
    return ApiResponse(success=True, data=payments, message="ok")


@router.get(
    "/fees",
    response_model=ApiResponse[list[FeeRead]],
    summary="List fee catalog",
)
def list_fees():
    return ApiResponse(success=True, data=payment_service.list_fees(), message="ok")


@router.post(
    "/fees",
    response_model=ApiResponse[FeeRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create fee catalog entry",
)
def create_fee(payload: FeeCreate, authorization: str = Header(default="")):
    require_role("professor", authorization)
    data = payment_service.create_fee(payload)
    return ApiResponse(success=True, data=data, message="created")


@router.put(
    "/fees/{fee_id}",
    response_model=ApiResponse[FeeRead],
    summary="Update fee catalog entry",
)
def update_fee(fee_id: int, payload: FeeUpdate, authorization: str = Header(default="")):
    require_role("professor", authorization)
    data = payment_service.update_fee(fee_id, payload)
    return ApiResponse(success=True, data=data, message="updated")


@router.delete(
    "/fees/{fee_id}",
    response_model=ApiResponse[DeleteData],
    summary="Delete fee catalog entry",
)
def delete_fee(fee_id: int, authorization: str = Header(default="")):
    require_role("professor", authorization)
    deleted = payment_service.delete_fee(fee_id)
    return ApiResponse(success=True, data=DeleteData(deleted=deleted, id=fee_id), message="deleted")


@router.post(
    "/orders",
    response_model=ApiResponse[OrderRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create payment order from courses",
)
def create_order(payload: OrderCreate, authorization: str = Header(default="")):
    auth_payload = require_role("student", authorization)
    data = payment_service.create_order(payload, auth_payload.get("email", "student"))
    return ApiResponse(success=True, data=data, message="created")


@router.post(
    "/payments/{payment_id}/pay",
    response_model=ApiResponse[ReceiptRead],
    summary="Pay a pending payment",
)
def pay(payment_id: int, payload: PayRequest, authorization: str = Header(default="")):
    auth_payload = require_role("student", authorization)
    data = payment_service.pay_payment(payment_id, payload, auth_payload.get("email"))
    return ApiResponse(success=True, data=data, message="paid")


@router.post(
    "/payments",
    response_model=ApiResponse[PaymentRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create payment",
)
def create_payment(payload: PaymentCreate, authorization: str = Header(default="")):
    require_auth(authorization)
    data = payment_service.create_payment(payload)
    return ApiResponse(success=True, data=data, message="created")


@router.get(
    "/payments/{payment_id}",
    response_model=ApiResponse[PaymentRead],
    summary="Get payment",
)
def get_payment(payment_id: int, authorization: str = Header(default="")):
    payload = require_auth(authorization)
    data = payment_service.get_payment(payment_id)
    if payload.get("role") == "student" and data.student_email != payload.get("email"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
    return ApiResponse(success=True, data=data, message="ok")


@router.put(
    "/payments/{payment_id}",
    response_model=ApiResponse[PaymentRead],
    summary="Update payment",
)
def update_payment(payment_id: int, payload: PaymentUpdate, authorization: str = Header(default="")):
    auth_payload = require_auth(authorization)
    role = auth_payload.get("role")
    email = auth_payload.get("email")
    if role == "student":
        payment = payment_service.get_payment(payment_id)
        if payment.student_email != email:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        if payment.status == "PAID":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="payment already paid")
        updates = payload.model_dump(exclude_unset=True)
        if "currency" in updates:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="currency update not allowed")
        if "status" in updates and updates["status"] not in ("PENDING", "CANCELLED"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid status")
        payload = PaymentUpdate(amount=updates.get("amount"), status=updates.get("status"))
    else:
        require_role("professor", authorization)
    data = payment_service.update_payment(payment_id, payload)
    return ApiResponse(success=True, data=data, message="updated")


@router.delete(
    "/payments/{payment_id}",
    response_model=ApiResponse[DeleteData],
    summary="Delete payment",
)
def delete_payment(payment_id: int, authorization: str = Header(default="")):
    auth_payload = require_auth(authorization)
    role = auth_payload.get("role")
    email = auth_payload.get("email")
    if role == "student":
        payment = payment_service.get_payment(payment_id)
        if payment.student_email != email:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        if payment.status == "PAID":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="payment already paid")
    else:
        require_role("professor", authorization)
    deleted = payment_service.delete_payment(payment_id)
    return ApiResponse(success=True, data=DeleteData(deleted=deleted, id=payment_id), message="deleted")


@router.post(
    "/paypal/order",
    response_model=ApiResponse[PaypalOrderResponse],
    summary="Create PayPal order (simulated)",
)
def create_paypal_order(payload: PaypalOrderRequest):
    data = payment_service.create_paypal_order(payload)
    return ApiResponse(success=True, data=data, message="order created")


@router.get(
    "/info",
    response_model=ApiResponse[InfoData],
    summary="Service info",
)
def info():
    return ApiResponse(
        success=True,
        data=InfoData(
            service="payment-service",
            entity="payment",
            endpoints={
                "list": "/api/payments",
                "create": "/api/payments",
                "get": "/api/payments/{payment_id}",
                "update": "/api/payments/{payment_id}",
                "delete": "/api/payments/{payment_id}",
                "paypal_order": "/api/paypal/order",
                "fees": "/api/fees",
                "fee_update": "/api/fees/{fee_id}",
                "fee_delete": "/api/fees/{fee_id}",
                "orders": "/api/orders",
                "pay": "/api/payments/{payment_id}/pay",
            },
        ),
        message="info ok",
    )
