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

logger = logging.getLogger("calendar-service")


class EventCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    date: str = Field(min_length=8, max_length=40)
    location: str = Field(min_length=2, max_length=120)


class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    date: Optional[str] = Field(default=None, min_length=8, max_length=40)
    location: Optional[str] = Field(default=None, min_length=2, max_length=120)


class EventRead(BaseModel):
    id: int
    student_email: str
    title: str
    date: str
    location: str


@dataclass
class CalendarService:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://auth_user:auth_pass@postgres:5432/auth_db")
    kafka_brokers: str = os.getenv("KAFKA_BROKERS", "kafka:9092")
    kafka_topic_events: str = os.getenv("KAFKA_TOPIC_CALENDAR_EVENTS", "calendar-events")
    kafka_topic_commands: str = os.getenv("KAFKA_TOPIC_CALENDAR_COMMANDS", "calendar-commands")
    rabbit_url: str = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
    rabbit_exchange: str = os.getenv("RABBIT_EXCHANGE", "commands")
    rabbit_queue: str = os.getenv("RABBIT_COMMAND_QUEUE", "calendar-commands")
    rabbit_routing_key: str = os.getenv("RABBIT_ROUTING_KEY", "calendar.command")

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

    def list_events(self, student_email: Optional[str] = None) -> list[EventRead]:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            if student_email:
                cur.execute(
                    "SELECT id, student_email, title, date, location FROM events WHERE student_email = %s ORDER BY id ASC",
                    (student_email,),
                )
            else:
                cur.execute("SELECT id, student_email, title, date, location FROM events ORDER BY id ASC")
            rows = cur.fetchall()
        return [EventRead(id=row[0], student_email=row[1], title=row[2], date=row[3], location=row[4]) for row in rows]

    def create_event(self, payload: EventCreate, student_email: str) -> EventRead:
        self._ensure_ready()
        self._publish_command("calendar.create_event", {"student_email": student_email, **payload.model_dump()})
        with self._db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (student_email, title, date, location)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (student_email, payload.title, payload.date, payload.location),
            )
            event_id = cur.fetchone()[0]
        event = EventRead(
            id=event_id,
            student_email=student_email,
            title=payload.title,
            date=payload.date,
            location=payload.location,
        )
        self._emit_event("event.created", event.model_dump())
        return event

    def get_event(self, event_id: int) -> EventRead:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            cur.execute(
                "SELECT id, student_email, title, date, location FROM events WHERE id = %s",
                (event_id,),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event not found")
        return EventRead(id=row[0], student_email=row[1], title=row[2], date=row[3], location=row[4])

    def update_event(self, event_id: int, payload: EventUpdate) -> EventRead:
        self._ensure_ready()
        self._publish_command("calendar.update_event", {"event_id": event_id, **payload.model_dump(exclude_unset=True)})
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return self.get_event(event_id)
        columns = ", ".join(f"{key} = %s" for key in updates.keys())
        values = list(updates.values())
        values.append(event_id)
        with self._db_conn.cursor() as cur:
            cur.execute(
                f"UPDATE events SET {columns} WHERE id = %s RETURNING id, student_email, title, date, location",
                values,
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event not found")
        event = EventRead(id=row[0], student_email=row[1], title=row[2], date=row[3], location=row[4])
        self._emit_event("event.updated", event.model_dump())
        return event

    def delete_event(self, event_id: int) -> bool:
        self._ensure_ready()
        self._publish_command("calendar.delete_event", {"event_id": event_id})
        with self._db_conn.cursor() as cur:
            cur.execute("DELETE FROM events WHERE id = %s", (event_id,))
            deleted = cur.rowcount == 1
        if deleted:
            self._emit_event("event.deleted", {"id": event_id})
        return deleted

    def _ensure_ready(self) -> None:
        if not self._db_conn or self._db_conn.closed:
            self._init_db()

    def _init_db(self) -> None:
        try:
            self._db_conn = psycopg.connect(self.database_url, autocommit=True)
            with self._db_conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id SERIAL PRIMARY KEY,
                        student_email TEXT NOT NULL,
                        title TEXT NOT NULL,
                        date TEXT NOT NULL,
                        location TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE events
                    ADD COLUMN IF NOT EXISTS student_email TEXT NOT NULL DEFAULT 'unknown'
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
                group_id="calendar-service",
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


calendar_service = CalendarService()
