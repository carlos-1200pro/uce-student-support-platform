# Notification Service
Sends notifications and handles webhook-style events.

## Tech
- FastAPI
- PostgreSQL (`DATABASE_URL`)
- Kafka/RabbitMQ for messaging (`KAFKA_BROKERS`, `RABBIT_URL`, etc.)

## Run locally
```bash
docker compose up notification-service
# or
uvicorn app.main:app --host 0.0.0.0 --port 8008
```

## Key endpoints
- `GET /health`
- `POST /notifications/api/...`
- `/api/webhooks` (inbound)

## Structure
- `app/main.py` — FastAPI app, routes
- `app/service.py` — business logic, DB/messaging
- `requirements.txt` — dependencies
- `Dockerfile` — container build
