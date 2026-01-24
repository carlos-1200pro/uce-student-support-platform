# Auth Service
Authenticates users, issues JWTs, and manages sessions.

## Tech
- FastAPI
- PostgreSQL (`DATABASE_URL`)
- Redis for sessions (`REDIS_URL`)
- Kafka/RabbitMQ for messaging (`KAFKA_BROKERS`, `RABBIT_URL`, etc.)

## Run locally
```bash
docker compose up auth-service
# or
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Key endpoints
- `GET /health`
- `POST /auth/api/login`
- `POST /auth/api/logout`

## Structure
- `app/main.py` — FastAPI app, routes
- `app/service.py` — business logic, DB/Redis/messaging
- `requirements.txt` — dependencies
- `Dockerfile` — container build
