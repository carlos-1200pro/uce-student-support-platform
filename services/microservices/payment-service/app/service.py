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

logger = logging.getLogger("payment-service")


class PaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: str = Field(default="PENDING", min_length=3, max_length=20)


class PaymentUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    status: Optional[str] = Field(default=None, min_length=3, max_length=20)


class PaymentRead(BaseModel):
    id: int
    student_email: Optional[str] = None
    amount: float
    currency: str
    status: str


class PaypalOrderRequest(BaseModel):
    amount: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class PaypalOrderResponse(BaseModel):
    order_id: str
    approval_url: str


class FeeCreate(BaseModel):
    course: str = Field(min_length=2, max_length=120)
    amount: float = Field(gt=0)


class FeeUpdate(BaseModel):
    course: Optional[str] = Field(default=None, min_length=2, max_length=120)
    amount: Optional[float] = Field(default=None, gt=0)


class FeeRead(BaseModel):
    id: int
    course: str
    amount: float


class OrderCreate(BaseModel):
    courses: list[int]


class OrderItem(BaseModel):
    course_id: int
    course: str
    amount: float


class OrderRead(BaseModel):
    payment_id: int
    total: float
    items: list[OrderItem]


class PayRequest(BaseModel):
    method: str = Field(min_length=3, max_length=20)
    card_last4: str = Field(min_length=4, max_length=4)
    cardholder: str = Field(min_length=3, max_length=120)
    expiry: str = Field(min_length=4, max_length=10)


class ReceiptRead(BaseModel):
    payment_id: int
    paid_at: str
    method: str
    card_last4: str

@dataclass
class PaymentService:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://auth_user:auth_pass@postgres:5432/auth_db")
    kafka_brokers: str = os.getenv("KAFKA_BROKERS", "kafka:9092")
    kafka_topic_events: str = os.getenv("KAFKA_TOPIC_PAYMENT_EVENTS", "payment-events")
    kafka_topic_commands: str = os.getenv("KAFKA_TOPIC_PAYMENT_COMMANDS", "payment-commands")
    rabbit_url: str = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
    rabbit_exchange: str = os.getenv("RABBIT_EXCHANGE", "commands")
    rabbit_queue: str = os.getenv("RABBIT_COMMAND_QUEUE", "payment-commands")
    rabbit_routing_key: str = os.getenv("RABBIT_ROUTING_KEY", "payment.command")
    default_fee_catalog: tuple[tuple[str, float], ...] = (
        ("Programacion distribuida", 120.0),
        ("Arquitectura de software", 110.0),
        ("Mineria de datos", 105.0),
        ("Control de seguridad", 100.0),
        ("Investigacion operativa", 95.0),
    )

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
        self._seed_default_fees()

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

    def list_payments(self, student_email: Optional[str] = None) -> list[PaymentRead]:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            if student_email:
                cur.execute(
                    "SELECT id, student_email, amount, currency, status FROM payments WHERE student_email = %s ORDER BY id ASC",
                    (student_email,),
                )
            else:
                cur.execute("SELECT id, student_email, amount, currency, status FROM payments ORDER BY id ASC")
            rows = cur.fetchall()
        return [
            PaymentRead(id=row[0], student_email=row[1], amount=row[2], currency=row[3], status=row[4])
            for row in rows
        ]

    def list_fees(self) -> list[FeeRead]:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            cur.execute("SELECT id, course, amount FROM fee_catalog ORDER BY id ASC")
            rows = cur.fetchall()
        return [FeeRead(id=row[0], course=row[1], amount=row[2]) for row in rows]

    def _get_fee(self, fee_id: int) -> FeeRead:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            cur.execute("SELECT id, course, amount FROM fee_catalog WHERE id = %s", (fee_id,))
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="fee not found")
        return FeeRead(id=row[0], course=row[1], amount=row[2])

    def create_fee(self, payload: FeeCreate) -> FeeRead:
        self._ensure_ready()
        self._publish_command("payment.create_fee", payload.model_dump())
        with self._db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fee_catalog (course, amount)
                VALUES (%s, %s)
                RETURNING id
                """,
                (payload.course, payload.amount),
            )
            fee_id = cur.fetchone()[0]
        fee = FeeRead(id=fee_id, course=payload.course, amount=payload.amount)
        self._emit_event("fee.created", fee.model_dump())
        return fee

    def update_fee(self, fee_id: int, payload: FeeUpdate) -> FeeRead:
        self._ensure_ready()
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return self._get_fee(fee_id)
        self._publish_command("payment.update_fee", {"fee_id": fee_id, **updates})
        columns = []
        values = []
        if "course" in updates:
            columns.append("course = %s")
            values.append(updates["course"])
        if "amount" in updates:
            columns.append("amount = %s")
            values.append(updates["amount"])
        values.append(fee_id)
        with self._db_conn.cursor() as cur:
            cur.execute(
                f"UPDATE fee_catalog SET {', '.join(columns)} WHERE id = %s RETURNING id, course, amount",
                tuple(values),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="fee not found")
        fee = FeeRead(id=row[0], course=row[1], amount=row[2])
        self._emit_event("fee.updated", fee.model_dump())
        return fee

    def delete_fee(self, fee_id: int) -> bool:
        self._ensure_ready()
        self._publish_command("payment.delete_fee", {"fee_id": fee_id})
        with self._db_conn.cursor() as cur:
            cur.execute("DELETE FROM fee_catalog WHERE id = %s", (fee_id,))
            deleted = cur.rowcount > 0
        if deleted:
            self._emit_event("fee.deleted", {"id": fee_id})
        return deleted

    def create_order(self, payload: OrderCreate, student_email: str) -> OrderRead:
        self._ensure_ready()
        self._publish_command("payment.create_order", {"student_email": student_email, **payload.model_dump()})
        if not payload.courses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="courses required")
        with self._db_conn.cursor() as cur:
            cur.execute(
                "SELECT id, course, amount FROM fee_catalog WHERE id = ANY(%s)",
                (payload.courses,),
            )
            rows = cur.fetchall()
        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="courses not found")
        items = [OrderItem(course_id=row[0], course=row[1], amount=float(row[2])) for row in rows]
        total = float(sum(item.amount for item in items))
        with self._db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO payments (student_email, amount, currency, status)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (student_email, total, "USD", "PENDING"),
            )
            payment_id = cur.fetchone()[0]
            for item in items:
                cur.execute(
                    """
                    INSERT INTO payment_items (payment_id, course_id, course, amount)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (payment_id, item.course_id, item.course, item.amount),
                )
        order = OrderRead(payment_id=payment_id, total=total, items=items)
        self._emit_event("payment.order_created", order.model_dump())
        return order

    def pay_payment(self, payment_id: int, payload: PayRequest, student_email: Optional[str] = None) -> ReceiptRead:
        self._ensure_ready()
        self._publish_command("payment.pay_payment", {"payment_id": payment_id, **payload.model_dump()})
        with self._db_conn.cursor() as cur:
            cur.execute("SELECT status, student_email FROM payments WHERE id = %s", (payment_id,))
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment not found")
        if student_email and row[1] != student_email:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        if row[0] == "PAID":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="payment already paid")
        with self._db_conn.cursor() as cur:
            cur.execute("UPDATE payments SET status = 'PAID' WHERE id = %s", (payment_id,))
            cur.execute(
                """
                INSERT INTO payment_receipts (payment_id, method, card_last4, cardholder, expiry)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING paid_at
                """,
                (payment_id, payload.method, payload.card_last4, payload.cardholder, payload.expiry),
            )
            paid_at = cur.fetchone()[0]
        receipt = ReceiptRead(
            payment_id=payment_id,
            paid_at=str(paid_at),
            method=payload.method,
            card_last4=payload.card_last4,
        )
        self._emit_event("payment.paid", receipt.model_dump())
        return receipt

    def create_payment(self, payload: PaymentCreate) -> PaymentRead:
        self._ensure_ready()
        self._publish_command("payment.create_payment", payload.model_dump())
        with self._db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO payments (amount, currency, status)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (payload.amount, payload.currency, payload.status),
            )
            payment_id = cur.fetchone()[0]
        payment = PaymentRead(
            id=payment_id,
            student_email=None,
            amount=payload.amount,
            currency=payload.currency,
            status=payload.status,
        )
        self._emit_event("payment.created", payment.model_dump())
        return payment

    def get_payment(self, payment_id: int) -> PaymentRead:
        self._ensure_ready()
        with self._db_conn.cursor() as cur:
            cur.execute(
                "SELECT id, student_email, amount, currency, status FROM payments WHERE id = %s",
                (payment_id,),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment not found")
        return PaymentRead(id=row[0], student_email=row[1], amount=row[2], currency=row[3], status=row[4])

    def update_payment(self, payment_id: int, payload: PaymentUpdate) -> PaymentRead:
        self._ensure_ready()
        self._publish_command("payment.update_payment", {"payment_id": payment_id, **payload.model_dump(exclude_unset=True)})
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return self.get_payment(payment_id)
        columns = ", ".join(f"{key} = %s" for key in updates.keys())
        values = list(updates.values())
        values.append(payment_id)
        with self._db_conn.cursor() as cur:
            cur.execute(
                f"UPDATE payments SET {columns} WHERE id = %s RETURNING id, student_email, amount, currency, status",
                values,
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment not found")
        payment = PaymentRead(id=row[0], student_email=row[1], amount=row[2], currency=row[3], status=row[4])
        self._emit_event("payment.updated", payment.model_dump())
        return payment

    def delete_payment(self, payment_id: int) -> bool:
        self._ensure_ready()
        self._publish_command("payment.delete_payment", {"payment_id": payment_id})
        with self._db_conn.cursor() as cur:
            cur.execute("DELETE FROM payments WHERE id = %s", (payment_id,))
            deleted = cur.rowcount == 1
        if deleted:
            self._emit_event("payment.deleted", {"id": payment_id})
        return deleted

    def create_paypal_order(self, payload: PaypalOrderRequest) -> PaypalOrderResponse:
        self._publish_command("payment.create_paypal_order", payload.model_dump())
        order_id = f"ORDER-{os.urandom(4).hex().upper()}"
        approval_url = f"http://localhost:8005/api/paypal/approve/{order_id}"
        self._emit_event(
            "paypal.order_created",
            {"order_id": order_id, "amount": payload.amount, "currency": payload.currency},
        )
        return PaypalOrderResponse(order_id=order_id, approval_url=approval_url)

    def _ensure_ready(self) -> None:
        if not self._db_conn or self._db_conn.closed:
            self._init_db()

    def _init_db(self) -> None:
        try:
            self._db_conn = psycopg.connect(self.database_url, autocommit=True)
            with self._db_conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS payments (
                        id SERIAL PRIMARY KEY,
                        student_email TEXT,
                        amount NUMERIC(10, 2) NOT NULL,
                        currency TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE payments
                    ADD COLUMN IF NOT EXISTS student_email TEXT
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS fee_catalog (
                        id SERIAL PRIMARY KEY,
                        course TEXT NOT NULL,
                        amount NUMERIC(10, 2) NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS payment_items (
                        id SERIAL PRIMARY KEY,
                        payment_id INT NOT NULL,
                        course_id INT NOT NULL,
                        course TEXT NOT NULL,
                        amount NUMERIC(10, 2) NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS payment_receipts (
                        id SERIAL PRIMARY KEY,
                        payment_id INT NOT NULL,
                        method TEXT NOT NULL,
                        card_last4 TEXT NOT NULL,
                        cardholder TEXT NOT NULL,
                        expiry TEXT NOT NULL,
                        paid_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
        except Exception as exc:
            logger.exception("Database init failed: %s", exc)
            raise

    def _seed_default_fees(self) -> None:
        if not self._db_conn:
            return
        try:
            with self._db_conn.cursor() as cur:
                cur.execute("SELECT course FROM fee_catalog")
                existing = {row[0].strip().lower() for row in cur.fetchall() if row[0]}
                for course, amount in self.default_fee_catalog:
                    if course.strip().lower() in existing:
                        continue
                    cur.execute(
                        "INSERT INTO fee_catalog (course, amount) VALUES (%s, %s)",
                        (course, amount),
                    )
        except Exception as exc:
            logger.warning("Seed fees skipped: %s", exc)

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
                group_id="payment-service",
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


payment_service = PaymentService()
