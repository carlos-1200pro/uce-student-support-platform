import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.router import ApiResponse, HealthData, router
from app.service import auth_service

load_dotenv()

SERVICE_NAME = os.getenv("SERVICE_NAME", "auth-service")

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
    auth_service.startup()


@app.on_event("shutdown")
def on_shutdown() -> None:
    auth_service.shutdown()


@app.get("/health", response_model=ApiResponse[HealthData], summary="Health check")
def health():
    return ApiResponse(
        success=True,
        data=HealthData(status="ok", service=SERVICE_NAME),
        message="ok",
    )


app.include_router(router, prefix="/api", tags=["auth"])
