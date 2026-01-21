import os
import time
from typing import Optional

import httpx
import jwt
import redis
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

SERVICE_NAME = os.getenv("SERVICE_NAME", "api-gateway")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

UPSTREAMS = {
    "auth": os.getenv("AUTH_URL"),
    "users": os.getenv("USER_URL"),
    "tutoring": os.getenv("TUTORING_URL"),
    "forum": os.getenv("FORUM_URL"),
    "payment": os.getenv("PAYMENT_URL"),
    "calendar": os.getenv("CALENDAR_URL"),
    "academic-record": os.getenv("ACADEMIC_RECORD_URL"),
    "notification": os.getenv("NOTIFICATION_URL"),
    "reporting": os.getenv("REPORTING_URL"),
    "audit": os.getenv("AUDIT_URL"),
}

redis_client: Optional[redis.Redis] = None

app = FastAPI(title=SERVICE_NAME, version="0.1.0")

ALLOWED_ORIGINS = [
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004",
    "http://localhost:3005",
    "http://localhost:3006",
    "http://localhost:3007",
    "http://localhost:3010",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    global redis_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)


@app.on_event("shutdown")
def on_shutdown() -> None:
    if redis_client:
        redis_client.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME, "upstreams": list(UPSTREAMS.keys())}


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_exempt_path(path: str) -> bool:
    return path in (
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/auth/login",
        "/auth/register",
        "/auth/api/login",
        "/auth/api/register",
        "/auth/health",
        "/auth/info",
        "/auth/api/info",
    )

def _apply_cors(response: Response, request: Request) -> Response:
    origin = request.headers.get("origin")
    if origin and origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "authorization,content-type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,PATCH,OPTIONS"
    return response


def _rate_limit(request: Request) -> Optional[Response]:
    if not redis_client:
        return None
    client_ip = _get_client_ip(request)
    window = int(time.time() // RATE_LIMIT_WINDOW_SECONDS)
    key = f"rate:{client_ip}:{window}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, RATE_LIMIT_WINDOW_SECONDS)
    if count > RATE_LIMIT_REQUESTS:
        response = Response(
            content=b'{"success":false,"data":null,"message":"rate limit exceeded"}',
            status_code=429,
            media_type="application/json",
        )
        return _apply_cors(response, request)
    return None


def _validate_jwt(request: Request) -> Optional[Response]:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        response = Response(
            content=b'{"success":false,"data":null,"message":"missing token"}',
            status_code=401,
            media_type="application/json",
        )
        return _apply_cors(response, request)
    token = auth_header.split(" ", 1)[1].strip()
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        response = Response(
            content=b'{"success":false,"data":null,"message":"invalid token"}',
            status_code=401,
            media_type="application/json",
        )
        return _apply_cors(response, request)
    if redis_client and not redis_client.exists(f"session:{token}"):
        response = Response(
            content=b'{"success":false,"data":null,"message":"session expired"}',
            status_code=401,
            media_type="application/json",
        )
        return _apply_cors(response, request)
    return None


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        response = await call_next(request)
        return _apply_cors(response, request)
    if not _is_exempt_path(request.url.path):
        rate_limited = _rate_limit(request)
        if rate_limited:
            return rate_limited
        invalid = _validate_jwt(request)
        if invalid:
            return invalid
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return _apply_cors(response, request)


async def forward(request: Request, base_url: str, path: str) -> Response:
    if not base_url:
        return Response(
            content=b'{"error":"upstream not configured"}',
            status_code=500,
            media_type="application/json",
        )

    url = f"{base_url}/{path}" if path else f"{base_url}/"

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=await request.body(),
            params=dict(request.query_params),
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]


@app.api_route("/{service}/{path:path}", methods=METHODS)
async def proxy(service: str, path: str, request: Request):
    base = UPSTREAMS.get(service)
    return await forward(request, base, path)


@app.api_route("/auth/{path:path}", methods=METHODS)
async def auth_alias(request: Request, path: str):
    return await forward(request, UPSTREAMS["auth"], path)


@app.api_route("/users/{path:path}", methods=METHODS)
async def users_alias(request: Request, path: str):
    return await forward(request, UPSTREAMS["users"], path)
