import json
import logging
import os
import threading
from dataclasses import dataclass
from typing import Optional

import psycopg
from fastapi import HTTPException, status
from kafka import KafkaConsumer, KafkaProducer
import pika
from pydantic import BaseModel, Field

logger = logging.getLogger("notification-service")


class NotificationCreate(BaseModel):
    to: str = Field(min_length=3, max_length=120)
    message: str = Field(min_length=1, max_length=500)
    level: str = Field(min_length=3, max_length=20)


class NotificationUpdate(BaseModel):
    to: Optional[str] = Field(default=None, min_length=3, max_length=120)
    message: Optional[str] = Field(default=None, min_length=1, max_length=500)
    level: Optional[str] = Field(default=None, min_length=3, max_length=20)


class NotificationRead(BaseModel):
    id: int
    to: str
    message: str
    level: str


class WebhookEventCreate(BaseModel):
    source: str = Field(min_length=3, max_length=120)
    payload: dict


class WebhookEventRead(BaseModel):
    id: int
    source: str
    payload: dict


@dataclass
class NotificationService:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://auth_user:auth_pass@postgres:5432/auth_db")
    kafka_brokers: str = os.getenv("KAFKA_BROKERS", "kafka:9092")
    kafka_topic_events: str = os.getenv("KAFKA_TOPIC_NOTIFICATION_EVENTS", "notification-events")
    kafka_topic_commands: str = os.getenv("KAFKA_TOPIC_NOTIFICATION_COMMANDS", "notification-commands")
    rabbit_url: str = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
    rabbit_exchange: str = os.getenv("RABBIT_EXCHANGE", "commands")
    rabbit_queue: str = os.getenv("RABBIT_COMMAND_QUEUE", "notification-commands")
    rabbit_routing_key: str = os.getenv("RABBIT_ROUTING_KEY", "notification.command")

    _db_conn: Optional[psycopg.Connection] = None
    _producer: Optional[KafkaProducer] = None
    _consumer_thread: Optional[threading.Thread] = None
    _consumer_running: Optional[threading.Event] = None
    _rabbit_conn: Optional[pika.BlockingConnection] = None
    _rabbit_channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

    def startup(self) -> None:
        self._init_db()
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
        if self._db_conn and not self._db_conn.closed:
            self._db_conn.close()

    def list_notifications(self) -> list[NotificationRead]:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            cur.execute("SELECT id, recipient, message, level FROM notifications ORDER BY id ASC")
            rows = cur.fetchall()
        return [NotificationRead(id=row[0], to=row[1], message=row[2], level=row[3]) for row in rows]

    def create_notification(self, payload: NotificationCreate) -> NotificationRead:
        self._ensure_ready()
        self._publish_command("notification.create", payload.model_dump())
        with self._db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notifications (recipient, message, level)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (payload.to, payload.message, payload.level),
            )
            notification_id = cur.fetchone()[0]
        notification = NotificationRead(
            id=notification_id,
            to=payload.to,
            message=payload.message,
            level=payload.level,
        )
        self._emit_event("notification.created", notification.model_dump())
        return notification

    def get_notification(self, notification_id: int) -> NotificationRead:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            cur.execute(
                "SELECT id, recipient, message, level FROM notifications WHERE id = %s",
                (notification_id,),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
        return NotificationRead(id=row[0], to=row[1], message=row[2], level=row[3])

    def update_notification(self, notification_id: int, payload: NotificationUpdate) -> NotificationRead:
        self._ensure_ready()
        self._publish_command("notification.update", {"notification_id": notification_id, **payload.model_dump(exclude_unset=True)})
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return self.get_notification(notification_id)
        if "to" in updates:
            updates["recipient"] = updates.pop("to")
        columns = ", ".join(f"{key} = %s" for key in updates.keys())
        values = list(updates.values())
        values.append(notification_id)
        with self._db_conn.cursor() as cur:
            cur.execute(
                f"UPDATE notifications SET {columns} WHERE id = %s RETURNING id, recipient, message, level",
                values,
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
        notification = NotificationRead(id=row[0], to=row[1], message=row[2], level=row[3])
        self._emit_event("notification.updated", notification.model_dump())
        return notification

    def delete_notification(self, notification_id: int) -> bool:
        self._ensure_ready()
        self._publish_command("notification.delete", {"notification_id": notification_id})
        with self._db_conn.cursor() as cur:
            cur.execute("DELETE FROM notifications WHERE id = %s", (notification_id,))
            deleted = cur.rowcount == 1
        if deleted:
            self._emit_event("notification.deleted", {"id": notification_id})
        return deleted

    def list_webhooks(self) -> list[WebhookEventRead]:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            cur.execute("SELECT id, source, payload FROM webhook_events ORDER BY id ASC")
            rows = cur.fetchall()
        return [
            WebhookEventRead(
                id=row[0],
                source=row[1],
                payload=row[2] if isinstance(row[2], dict) else json.loads(row[2]),
            )
            for row in rows
        ]

    def create_webhook(self, payload: WebhookEventCreate) -> WebhookEventRead:
        self._ensure_ready()
        self._publish_command("notification.webhook", payload.model_dump())
        with self._db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO webhook_events (source, payload)
                VALUES (%s, %s)
                RETURNING id
                """,
                (payload.source, json.dumps(payload.payload)),
            )
            event_id = cur.fetchone()[0]
        event = WebhookEventRead(id=event_id, source=payload.source, payload=payload.payload)
        self._emit_event("webhook.received", event.model_dump())
        return event

    def get_webhook(self, event_id: int) -> WebhookEventRead:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            cur.execute("SELECT id, source, payload FROM webhook_events WHERE id = %s", (event_id,))
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="webhook not found")
        payload = row[2] if isinstance(row[2], dict) else json.loads(row[2])
        return WebhookEventRead(id=row[0], source=row[1], payload=payload)

    def _ensure_ready(self) -> None:
        if not self._db_conn or self._db_conn.closed:
            self._init_db()

    def _init_db(self) -> None:
        try:
            self._db_conn = psycopg.connect(self.database_url, autocommit=True)
            with self._db_conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notifications (
                        id SERIAL PRIMARY KEY,
                        recipient TEXT NOT NULL,
                        message TEXT NOT NULL,
                        level TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS webhook_events (
                        id SERIAL PRIMARY KEY,
                        source TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
        except Exception as exc:
            logger.exception("Database init failed: %s", exc)
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
                group_id="notification-service",
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


notification_service = NotificationService()
