import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.router import ApiResponse, HealthData, router
from app.service import user_service

load_dotenv()

SERVICE_NAME = os.getenv("SERVICE_NAME", "user-service")
BASE_PATH = os.getenv("BASE_PATH", "").rstrip("/")
if BASE_PATH and not BASE_PATH.startswith("/"):
    BASE_PATH = f"/{BASE_PATH}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

app = FastAPI(title=SERVICE_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    user_service.startup()


@app.on_event("shutdown")
def on_shutdown() -> None:
    user_service.shutdown()


@app.get(f"{BASE_PATH}/health" if BASE_PATH else "/health", response_model=ApiResponse[HealthData], summary="Health check")
def health():
    return ApiResponse(
        success=True,
        data=HealthData(status="ok", service=SERVICE_NAME),
        message="ok",
    )


app.include_router(router, prefix=f"{BASE_PATH}/api" if BASE_PATH else "/api", tags=["user"])
