# Payment Service
Manages payments, fees, orders, and emits events.

## Tech
- FastAPI
- PostgreSQL (`DATABASE_URL`)
- Kafka (`KAFKA_BROKERS`, topics `payment-events`, `payment-commands`)
- RabbitMQ (`RABBIT_URL`, exchange `commands`, queue `payment-commands`, routing `payment.command`)

## Run locally
```bash
docker compose up payment-service
# or
uvicorn app.main:app --host 0.0.0.0 --port 8005
```

## Key endpoints
- `GET /health`
- `POST /payments/api/orders`
- `POST /payments/api/payments/{id}/pay`

## Structure
- `app/main.py` — FastAPI app, routes
- `app/service.py` — business logic, DB, Kafka/Rabbit integration
- `requirements.txt` — dependencies
- `Dockerfile` — container build
