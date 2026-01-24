# Forum Service
Provides forum posts and comments.

## Tech
- FastAPI
- MongoDB (`MONGO_URI`, `MONGO_DB`, `MONGO_COLLECTION`, `MONGO_COMMENTS`)
- Kafka/RabbitMQ for messaging (`KAFKA_BROKERS`, `RABBIT_URL`, etc.)

## Run locally
```bash
docker compose up forum-service
# or
uvicorn app.main:app --host 0.0.0.0 --port 8004
```

## Key endpoints
- `GET /health`
- `GET /forum/api/posts`
- `POST /forum/api/posts`

## Structure
- `app/main.py` — FastAPI app, routes
- `app/service.py` — business logic, Mongo/messaging
- `requirements.txt` — dependencies
- `Dockerfile` — container build
