# UCE Student Support Platform

Monorepo with Turborepo, FastAPI microservices, frontends, and AWS infrastructure managed by Terraform. Messaging uses Kafka and RabbitMQ; data uses PostgreSQL, MongoDB, and Redis.

## Architecture (cloud)
- **VPCs**: two VPCs. Lab1 (backend) is private; Lab2 (frontend) is public.
- **Ingress**: public ALB (Lab2) → API Gateway EC2 (Nginx, EIP) → internal ALB → private microservices.
- **Data stack**: EC2 (10.10.11.25) running PostgreSQL, Redis, MongoDB.
- **Messaging stack**: EC2 (10.10.12.238) running Zookeeper/Kafka/RabbitMQ.
- **Microservices**: 5 private EC2s (pairs of services) behind internal ALB.
- **Frontends**: 4 public EC2s behind public ALB.
- **Bastion**: public EC2 for SSH and outbound for private subnets.
- **Security Groups**: segmented per role (gateway, internal ALB, services, db, redis, mongo, kafka, rabbit, bastion).
- **Instance types**: t3.medium for messaging (RAM), t3.small for data/services, t3.micro for gateway/bastion/frontends.

## Services and data stores
- PostgreSQL: auth, user, calendar, academic-record, tutoring, notification, audit, reporting, payment.
- MongoDB: forum.
- Redis: auth (sessions).
- Messaging: Kafka topics `payment-events`, `payment-commands`; Rabbit exchange `commands`, queue `payment-commands`.

## Local development
```bash
# run everything with Docker
docker compose up --build
```
Health checks (examples):
- Gateway: http://localhost:8080/health
- Auth: http://localhost:8080/auth/health
- Payment: http://localhost:8080/payments/health

Notes:
- Postgres is exposed on 5433 (conflicts avoided with local Postgres).
- All services expose `GET /health`; API paths are under `/api/...`.

## Turborepo
- Run tasks in parallel with cache reuse: `npx turbo run build`, `npx turbo run lint`.
- Filter to a single package/service: `npx turbo run test --filter=payment-service`.

## CI/CD
- GitHub Actions (in `.github/workflows/`) run lint/test/build. They leverage Turbo cache for faster PR checks.

## Terraform (infra/)
- Modules: network, security_groups, bastion, data_stack, messaging_stack, private_ec2_services, internal_alb, gateway_ec2, frontend_ec2, frontend_alb.
- Variables set in `terraform.tfvars` (region, CIDRs, instance types, fixed IPs for data/messaging, DB creds).
- Typical workflow:
  ```bash
  terraform init
  terraform plan
  terraform apply
  ```

## Frontends
Static frontends built with Vite and served by Nginx; they call the gateway base URL (EIP in cloud, localhost in local compose).
