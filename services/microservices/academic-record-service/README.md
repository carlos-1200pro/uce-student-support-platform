# Academic Record Service
Manages student academic records.

## Tech
- FastAPI
- PostgreSQL (`DATABASE_URL`)
- Kafka/RabbitMQ for messaging (`KAFKA_BROKERS`, `RABBIT_URL`, etc.)

## Run locally
```bash
docker compose up academic-record-service
# or
uvicorn app.main:app --host 0.0.0.0 --port 8007
```

## Key endpoints
- `GET /health`
- `GET/POST /records/api/...`

## Structure
- `app/main.py` — FastAPI app, routes
- `app/service.py` — business logic, DB/messaging
- `requirements.txt` — dependencies
- `Dockerfile` — container build
