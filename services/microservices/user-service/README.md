# User Service
Manages user profiles and related CRUD.

## Tech
- FastAPI
- PostgreSQL (`DATABASE_URL`)
- Kafka/RabbitMQ for messaging (`KAFKA_BROKERS`, `RABBIT_URL`, etc.)

## Run locally
```bash
docker compose up user-service
# or
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

## Key endpoints
- `GET /health`
- `GET /users/api/users`
- `POST /users/api/users`

## Structure
- `app/main.py` — FastAPI app, routes
- `app/service.py` — business logic, DB/messaging
- `requirements.txt` — dependencies
- `Dockerfile` — container build
