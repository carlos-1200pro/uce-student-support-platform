# API Gateway
Nginx reverse proxy for all backend services.

## Purpose
- Exposes a single entrypoint (port 8080) for all microservices.
- Routes paths to internal services (auth, user, forum, tutoring, payment, calendar, academic-record, notification, reporting, audit).
- Applies JWT validation and basic security headers.

## Run locally
```bash
docker compose up api-gateway
```

## Config
- Environment in `.env` (base URL, JWT settings, rate limiting).
- Nginx config templates live in this folder; built into the image.

## Structure
- `Dockerfile` — builds Nginx with configs
- `.env` — gateway settings
- Path mapping aligns with service base paths: `/auth`, `/users`, `/forum`, `/tutoring`, `/payments`, `/calendar`, `/records`, `/notifications`, `/reporting`, `/audit`.
