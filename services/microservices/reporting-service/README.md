# Reporting Service
Generates reports and aggregates data.

## Tech
- FastAPI
- PostgreSQL (`DATABASE_URL`)
- Kafka/RabbitMQ for messaging (`KAFKA_BROKERS`, `RABBIT_URL`, etc.)

## Run locally
```bash
docker compose up reporting-service
# or
uvicorn app.main:app --host 0.0.0.0 --port 8009
```

## Key endpoints
- `GET /health`
- `GET /reporting/api/...`

## Structure
- `app/main.py` — FastAPI app, routes
- `app/service.py` — business logic, DB/messaging
- `requirements.txt` — dependencies
- `Dockerfile` — container build
