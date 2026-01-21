# UCE Student Support Platform (Full Local + Docker)

This repo is a **fully runnable local + Docker** template with:
- **10 FastAPI microservices** (each has real endpoints + PostgreSQL/Mongo/Redis)
- **Internal API Gateway** (proxy) on **8080**
- **Static frontends** (Nginx) per module (simple UI + calls the gateway)
- **Docker Compose** to run everything locally

## Run locally with Docker
```bash
docker compose up --build
```

## QA smoke test (Windows PowerShell)
```powershell
./scripts/qa-smoke.ps1
```

## Health checks
- Gateway: http://localhost:8080/health
- Auth (via gateway): http://localhost:8080/auth/health
- Tutoring (direct): http://localhost:8003/health

## Notes
- Postgres container is exposed on port `5433` to avoid conflict with local Postgres.
- pgAdmin connection for Docker: host `localhost`, port `5433`, db `student_platform`.
- All services expose `GET /health` and basic CRUD endpoints under `/api/...`
- Gateway enforces JWT and rate limiting (Redis-backed).
- Notification service exposes `/api/webhooks` to receive external webhook events.

## Security (QA)
- JWT issued by auth-service and validated in api-gateway.
- Rate limiting per IP via Redis (`RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS`).
- Basic security headers added in api-gateway middleware.

## Frontends
These frontends are **real JavaScript apps** built with **Vite (vanilla JS)** and served by Nginx.
