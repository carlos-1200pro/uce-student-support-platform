# Tutoring Service
Handles tutoring sessions, scheduling, and related data.

## Tech
- FastAPI
- PostgreSQL (`DATABASE_URL`)
- Kafka/RabbitMQ for messaging (`KAFKA_BROKERS`, `RABBIT_URL`, etc.)

## Run locally
```bash
docker compose up tutoring-service
# or
uvicorn app.main:app --host 0.0.0.0 --port 8003
```

## Key endpoints
- `GET /health`
- `GET /tutoring/api/...` (sessions, tutors, etc.)

## Structure
- `app/main.py` — FastAPI app, routes
- `app/service.py` — business logic, DB/messaging
- `requirements.txt` — dependencies
- `Dockerfile` — container build
