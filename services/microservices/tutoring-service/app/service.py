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

logger = logging.getLogger("tutoring-service")


class TutoringCreate(BaseModel):
    teacher: str = Field(min_length=2, max_length=120)
    date: str = Field(min_length=8, max_length=40)


class TutoringUpdate(BaseModel):
    teacher: Optional[str] = Field(default=None, min_length=2, max_length=120)
    date: Optional[str] = Field(default=None, min_length=8, max_length=40)


class TutoringRead(BaseModel):
    id: int
    teacher: str
    teacher_email: str
    student: str
    date: str


class TicketRead(BaseModel):
    id: int
    session_id: int
    teacher: str
    teacher_email: str
    student: str
    date: str
    issued_at: str

@dataclass
class TutoringService:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://auth_user:auth_pass@postgres:5432/auth_db")
    kafka_brokers: str = os.getenv("KAFKA_BROKERS", "kafka:9092")
    kafka_topic_events: str = os.getenv("KAFKA_TOPIC_TUTORING_EVENTS", "tutoring-events")
    kafka_topic_commands: str = os.getenv("KAFKA_TOPIC_TUTORING_COMMANDS", "tutoring-commands")
    rabbit_url: str = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
    rabbit_exchange: str = os.getenv("RABBIT_EXCHANGE", "commands")
    rabbit_queue: str = os.getenv("RABBIT_COMMAND_QUEUE", "tutoring-commands")
    rabbit_routing_key: str = os.getenv("RABBIT_ROUTING_KEY", "tutoring.command")

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

    def list_sessions(self, teacher_email: Optional[str] = None) -> list[TutoringRead]:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            if teacher_email:
                cur.execute(
                    "SELECT id, teacher, teacher_email, student, date FROM tutoring_sessions WHERE teacher_email = %s ORDER BY id ASC",
                    (teacher_email,),
                )
            else:
                cur.execute("SELECT id, teacher, teacher_email, student, date FROM tutoring_sessions ORDER BY id ASC")
            rows = cur.fetchall()
        return [TutoringRead(id=row[0], teacher=row[1], teacher_email=row[2], student=row[3], date=row[4]) for row in rows]

    def create_session(self, payload: TutoringCreate, teacher_email: str) -> TutoringRead:
        self._ensure_ready()
        self._publish_command("tutoring.create_session", {**payload.model_dump(), "teacher_email": teacher_email})
        student = "DISPONIBLE"
        with self._db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tutoring_sessions (teacher, teacher_email, student, date)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (payload.teacher, teacher_email, student, payload.date),
            )
            session_id = cur.fetchone()[0]
        session = TutoringRead(
            id=session_id,
            teacher=payload.teacher,
            teacher_email=teacher_email,
            student=student,
            date=payload.date,
        )
        self._emit_event("tutoring.created", session.model_dump())
        return session

    def get_session(self, session_id: int) -> TutoringRead:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            cur.execute(
                "SELECT id, teacher, teacher_email, student, date FROM tutoring_sessions WHERE id = %s",
                (session_id,),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
        return TutoringRead(id=row[0], teacher=row[1], teacher_email=row[2], student=row[3], date=row[4])

    def update_session(self, session_id: int, payload: TutoringUpdate) -> TutoringRead:
        self._ensure_ready()
        self._publish_command("tutoring.update_session", {"session_id": session_id, **payload.model_dump(exclude_unset=True)})
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return self.get_session(session_id)
        columns = ", ".join(f"{key} = %s" for key in updates.keys())
        values = list(updates.values())
        values.append(session_id)
        with self._db_conn.cursor() as cur:
            cur.execute(
                f"UPDATE tutoring_sessions SET {columns} WHERE id = %s RETURNING id, teacher, teacher_email, student, date",
                values,
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
        session = TutoringRead(id=row[0], teacher=row[1], teacher_email=row[2], student=row[3], date=row[4])
        self._emit_event("tutoring.updated", session.model_dump())
        return session

    def reserve_session(self, session_id: int, student: str) -> TutoringRead:
        self._ensure_ready()
        self._publish_command("tutoring.reserve_session", {"session_id": session_id, "student": student})
        with self._db_conn.cursor() as cur:
            cur.execute(
                "SELECT teacher, teacher_email, student, date FROM tutoring_sessions WHERE id = %s",
                (session_id,),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
        if row[2].upper() != "DISPONIBLE":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="session already reserved")
        with self._db_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE tutoring_sessions
                SET student = %s
                WHERE id = %s
                RETURNING id, teacher, teacher_email, student, date
                """,
                (student, session_id),
            )
            updated = cur.fetchone()
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
        session = TutoringRead(
            id=updated[0],
            teacher=updated[1],
            teacher_email=updated[2],
            student=updated[3],
            date=updated[4],
        )
        with self._db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tutoring_tickets (session_id, teacher, teacher_email, student, date)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (session.id, session.teacher, session.teacher_email, session.student, session.date),
            )
        self._emit_event("tutoring.ticket_issued", session.model_dump())
        self._emit_event("tutoring.reserved", session.model_dump())
        return session

    def delete_session(self, session_id: int) -> bool:
        self._ensure_ready()
        self._publish_command("tutoring.delete_session", {"session_id": session_id})
        with self._db_conn.cursor() as cur:
            cur.execute("DELETE FROM tutoring_sessions WHERE id = %s", (session_id,))
            deleted = cur.rowcount == 1
        if deleted:
            self._emit_event("tutoring.deleted", {"id": session_id})
        return deleted

    def list_tickets(
        self, student_email: Optional[str] = None, teacher_email: Optional[str] = None
    ) -> list[TicketRead]:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            if student_email:
                cur.execute(
                    """
                    SELECT id, session_id, teacher, teacher_email, student, date, issued_at
                    FROM tutoring_tickets
                    WHERE student = %s
                    ORDER BY id DESC
                    """,
                    (student_email,),
                )
            elif teacher_email:
                cur.execute(
                    """
                    SELECT id, session_id, teacher, teacher_email, student, date, issued_at
                    FROM tutoring_tickets
                    WHERE teacher_email = %s
                    ORDER BY id DESC
                    """,
                    (teacher_email,),
                )
            else:
                cur.execute(
                    "SELECT id, session_id, teacher, teacher_email, student, date, issued_at FROM tutoring_tickets ORDER BY id DESC"
                )
            rows = cur.fetchall()
        return [
            TicketRead(
                id=row[0],
                session_id=row[1],
                teacher=row[2],
                teacher_email=row[3],
                student=row[4],
                date=row[5],
                issued_at=str(row[6]),
            )
            for row in rows
        ]

    def get_ticket(self, ticket_id: int) -> TicketRead:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            cur.execute(
                "SELECT id, session_id, teacher, teacher_email, student, date, issued_at FROM tutoring_tickets WHERE id = %s",
                (ticket_id,),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ticket not found")
        return TicketRead(
            id=row[0],
            session_id=row[1],
            teacher=row[2],
            teacher_email=row[3],
            student=row[4],
            date=row[5],
            issued_at=str(row[6]),
        )

    def _ensure_ready(self) -> None:
        if not self._db_conn or self._db_conn.closed:
            self._init_db()

    def _init_db(self) -> None:
        try:
            self._db_conn = psycopg.connect(self.database_url, autocommit=True)
            with self._db_conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tutoring_sessions (
                        id SERIAL PRIMARY KEY,
                        teacher TEXT NOT NULL,
                        teacher_email TEXT NOT NULL,
                        student TEXT NOT NULL,
                        date TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE tutoring_sessions
                    ADD COLUMN IF NOT EXISTS teacher_email TEXT NOT NULL DEFAULT ''
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tutoring_tickets (
                        id SERIAL PRIMARY KEY,
                        session_id INT NOT NULL,
                        teacher TEXT NOT NULL,
                        teacher_email TEXT NOT NULL,
                        student TEXT NOT NULL,
                        date TEXT NOT NULL,
                        issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE tutoring_tickets
                    ADD COLUMN IF NOT EXISTS teacher_email TEXT NOT NULL DEFAULT ''
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
                group_id="tutoring-service",
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


tutoring_service = TutoringService()
