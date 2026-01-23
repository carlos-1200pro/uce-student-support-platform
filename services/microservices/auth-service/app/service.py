import hashlib
import json
import logging
import os
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import psycopg
import redis
from fastapi import HTTPException, status
from kafka import KafkaConsumer, KafkaProducer
import jwt
import pika
from pydantic import BaseModel, EmailStr, Field
from typing import Literal

logger = logging.getLogger("auth-service")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)


class LoginData(BaseModel):
    user_id: int
    email: EmailStr
    full_name: str
    role: str
    status: str
    token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)
    full_name: str = Field(min_length=3, max_length=120)
    role: Literal["student", "professor"] = "student"


class RegisterData(BaseModel):
    user_id: int
    email: EmailStr
    full_name: str
    role: str


class LogoutRequest(BaseModel):
    token: str = Field(min_length=16)


class LogoutData(BaseModel):
    revoked: bool


@dataclass
class AuthService:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://auth_user:auth_pass@postgres:5432/auth_db")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    kafka_brokers: str = os.getenv("KAFKA_BROKERS", "kafka:9092")
    kafka_topic_events: str = os.getenv("KAFKA_TOPIC_AUTH_EVENTS", "auth-events")
    kafka_topic_commands: str = os.getenv("KAFKA_TOPIC_AUTH_COMMANDS", "auth-commands")
    rabbit_url: str = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
    rabbit_exchange: str = os.getenv("RABBIT_EXCHANGE", "commands")
    rabbit_queue: str = os.getenv("RABBIT_COMMAND_QUEUE", "auth-commands")
    rabbit_routing_key: str = os.getenv("RABBIT_ROUTING_KEY", "auth.command")
    password_salt: str = os.getenv("PASSWORD_SALT", "change-me")
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")

    _db_conn: Optional[psycopg.Connection] = None
    _redis: Optional[redis.Redis] = None
    _producer: Optional[KafkaProducer] = None
    _consumer_thread: Optional[threading.Thread] = None
    _consumer_running: Optional[threading.Event] = None
    _rabbit_conn: Optional[pika.BlockingConnection] = None
    _rabbit_channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

    def startup(self) -> None:
        self._init_db()
        self._seed_admin_user()
        self._init_redis()
        self._init_kafka()
        self._init_rabbit()
        self._start_consumer()

    def shutdown(self) -> None:
        if self._consumer_running:
            self._consumer_running.clear()
        if self._consumer_thread and self._consumer_thread.is_alive():
            self._consumer_thread.join(timeout=2)
        if self._producer:
            self._producer.flush(timeout=2)
            self._producer.close()
        if self._rabbit_channel:
            self._rabbit_channel.close()
        if self._rabbit_conn and self._rabbit_conn.is_open:
            self._rabbit_conn.close()
        if self._redis:
            self._redis.close()
        if self._db_conn and not self._db_conn.closed:
            self._db_conn.close()

    def register(self, payload: RegisterRequest) -> RegisterData:
        self._ensure_ready()
        self._publish_command("auth.register", payload.model_dump())
        with self._db_conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (payload.email,))
            if cur.fetchone():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already exists")
            password_hash = self._hash_password(payload.password)
            cur.execute(
                """
                INSERT INTO users (email, full_name, password_hash, role)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (payload.email, payload.full_name, password_hash, payload.role),
            )
            user_id = cur.fetchone()[0]
        self._emit_event("user.registered", {"user_id": user_id, "email": payload.email})
        return RegisterData(
            user_id=user_id,
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
        )

    def login(self, payload: LoginRequest) -> LoginData:
        self._ensure_ready()
        self._publish_command("auth.login", payload.model_dump())
        with self._db_conn.cursor() as cur:
            cur.execute(
                "SELECT id, password_hash, full_name, role, status FROM users WHERE email = %s",
                (payload.email,),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
        user_id, password_hash, full_name, role, status_value = row
        if status_value != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user blocked")
        if password_hash != self._hash_password(payload.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
        token = self._generate_token(user_id=user_id, email=payload.email, role=role)
        self._redis.setex(f"session:{token}", self.session_ttl_seconds, str(user_id))
        self._emit_event("user.logged_in", {"user_id": user_id, "email": payload.email})
        return LoginData(
            user_id=user_id,
            email=payload.email,
            full_name=full_name,
            role=role,
            status=status_value,
            token=token,
        )

    def logout(self, payload: LogoutRequest) -> LogoutData:
        self._ensure_ready()
        self._publish_command("auth.logout", payload.model_dump())
        deleted = self._redis.delete(f"session:{payload.token}") == 1
        if deleted:
            self._emit_event("user.logged_out", {"token": payload.token})
        return LogoutData(revoked=deleted)

    def _ensure_ready(self) -> None:
        if not self._db_conn or self._db_conn.closed:
            self._init_db()
        if not self._redis:
            self._init_redis()

    def _init_db(self) -> None:
        try:
            self._db_conn = psycopg.connect(self.database_url, autocommit=True)
            with self._db_conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        full_name TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'student',
                        status TEXT NOT NULL DEFAULT 'active',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'student'")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active'")
        except Exception as exc:
            logger.exception("Database init failed: %s", exc)
            raise

    def _seed_admin_user(self) -> None:
        if not self._db_conn:
            return
        with self._db_conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", ("admin@uce.edu.ec",))
            if cur.fetchone():
                return
            password_hash = self._hash_password("admin")
            cur.execute(
                """
                INSERT INTO users (email, full_name, password_hash, role, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                ("admin@uce.edu.ec", "Administrador UCE", password_hash, "admin", "active"),
            )

    def _init_redis(self) -> None:
        self._redis = redis.from_url(self.redis_url, decode_responses=True)
        try:
            self._redis.ping()
        except Exception as exc:
            logger.exception("Redis init failed: %s", exc)
            raise

    def _init_kafka(self) -> None:
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=self.kafka_brokers.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        except Exception as exc:
            logger.warning("Kafka producer unavailable: %s", exc)
            self._producer = None

    def _init_rabbit(self) -> None:
        try:
            self._rabbit_conn = pika.BlockingConnection(pika.URLParameters(self.rabbit_url))
            self._rabbit_channel = self._rabbit_conn.channel()
            self._rabbit_channel.exchange_declare(exchange=self.rabbit_exchange, exchange_type="topic", durable=True)
            self._rabbit_channel.queue_declare(queue=self.rabbit_queue, durable=True)
            self._rabbit_channel.queue_bind(
                exchange=self.rabbit_exchange,
                queue=self.rabbit_queue,
                routing_key=self.rabbit_routing_key,
            )
        except Exception as exc:
            logger.warning("RabbitMQ unavailable: %s", exc)
            self._rabbit_conn = None
            self._rabbit_channel = None

    def _start_consumer(self) -> None:
        if self._consumer_thread and self._consumer_thread.is_alive():
            return
        self._consumer_running = threading.Event()
        self._consumer_running.set()
        self._consumer_thread = threading.Thread(target=self._consume_commands, daemon=True)
        self._consumer_thread.start()

    def _consume_commands(self) -> None:
        try:
            consumer = KafkaConsumer(
                self.kafka_topic_commands,
                bootstrap_servers=self.kafka_brokers.split(","),
                group_id="auth-service",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            )
        except Exception as exc:
            logger.warning("Kafka consumer unavailable: %s", exc)
            return
        while self._consumer_running and self._consumer_running.is_set():
            records = consumer.poll(timeout_ms=500)
            for messages in records.values():
                for message in messages:
                    logger.info("Kafka command received: %s", message.value)
        consumer.close()

    def _emit_event(self, event_type: str, payload: dict) -> None:
        if not self._producer:
            return
        message = {"type": event_type, "payload": payload}
        self._producer.send(self.kafka_topic_events, message)

    def _publish_command(self, command: str, payload: dict) -> None:
        if not self._rabbit_channel or self._rabbit_channel.is_closed:
            return
        message = {"command": command, "payload": payload}
        try:
            self._rabbit_channel.basic_publish(
                exchange=self.rabbit_exchange,
                routing_key=self.rabbit_routing_key,
                body=json.dumps(message).encode("utf-8"),
            )
        except Exception as exc:
            logger.warning("RabbitMQ publish failed: %s", exc)
            if self._rabbit_conn and self._rabbit_conn.is_open:
                self._rabbit_conn.close()
            self._rabbit_conn = None
            self._rabbit_channel = None

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(f"{self.password_salt}{password}".encode("utf-8")).hexdigest()

    def _generate_token(self, user_id: int, email: str, role: str) -> str:
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(seconds=self.session_ttl_seconds)
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)


auth_service = AuthService()
