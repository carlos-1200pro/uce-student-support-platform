import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status
from kafka import KafkaConsumer, KafkaProducer
import pika
from pydantic import BaseModel, Field
from pymongo import MongoClient

logger = logging.getLogger("forum-service")


class PostCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=1)
    author: str = Field(min_length=3, max_length=120)


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1)


class PostRead(BaseModel):
    id: str
    title: str
    content: str
    author: str
    created_at: str


class CommentCreate(BaseModel):
    author: str = Field(min_length=3, max_length=120)
    content: str = Field(min_length=1, max_length=500)


class CommentRead(BaseModel):
    id: str
    post_id: str
    author: str
    content: str
    created_at: str


@dataclass
class ForumService:
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://mongo:27017")
    mongo_db: str = os.getenv("MONGO_DB", "forum_db")
    mongo_collection: str = os.getenv("MONGO_COLLECTION", "posts")
    mongo_comments: str = os.getenv("MONGO_COMMENTS", "comments")
    kafka_brokers: str = os.getenv("KAFKA_BROKERS", "kafka:9092")
    kafka_topic_events: str = os.getenv("KAFKA_TOPIC_FORUM_EVENTS", "forum-events")
    kafka_topic_commands: str = os.getenv("KAFKA_TOPIC_FORUM_COMMANDS", "forum-commands")
    rabbit_url: str = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
    rabbit_exchange: str = os.getenv("RABBIT_EXCHANGE", "commands")
    rabbit_queue: str = os.getenv("RABBIT_COMMAND_QUEUE", "forum-commands")
    rabbit_routing_key: str = os.getenv("RABBIT_ROUTING_KEY", "forum.command")

    _mongo: Optional[MongoClient] = None
    _producer: Optional[KafkaProducer] = None
    _consumer_thread: Optional[threading.Thread] = None
    _consumer_running: Optional[threading.Event] = None
    _rabbit_conn: Optional[pika.BlockingConnection] = None
    _rabbit_channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

    def startup(self) -> None:
        self._init_mongo()
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
        if self._mongo:
            self._mongo.close()

    def list_posts(self) -> list[PostRead]:
        self._ensure_ready()
        collection = self._collection()
        posts = []
        for doc in collection.find().sort("created_at", -1):
            posts.append(self._to_read(doc))
        return posts

    def create_post(self, payload: PostCreate) -> PostRead:
        self._ensure_ready()
        self._publish_command("forum.create_post", payload.model_dump())
        collection = self._collection()
        created_at = datetime.now(timezone.utc).isoformat()
        doc = payload.model_dump()
        doc["created_at"] = created_at
        result = collection.insert_one(doc)
        post = PostRead(id=str(result.inserted_id), **doc)
        self._emit_event("post.created", post.model_dump())
        return post

    def get_post(self, post_id: str) -> PostRead:
        self._ensure_ready()
        collection = self._collection()
        doc = collection.find_one({"_id": self._to_object_id(post_id)})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="post not found")
        return self._to_read(doc)

    def list_comments(self, post_id: str) -> list[CommentRead]:
        self._ensure_ready()
        collection = self._mongo[self.mongo_db][self.mongo_comments]
        comments = []
        for doc in collection.find({"post_id": post_id}).sort("created_at", 1):
            comments.append(
                CommentRead(
                    id=str(doc["_id"]),
                    post_id=doc["post_id"],
                    author=doc["author"],
                    content=doc["content"],
                    created_at=doc["created_at"],
                )
            )
        return comments

    def add_comment(self, post_id: str, payload: CommentCreate) -> CommentRead:
        self._ensure_ready()
        self._publish_command("forum.add_comment", {"post_id": post_id, **payload.model_dump()})
        collection = self._mongo[self.mongo_db][self.mongo_comments]
        created_at = datetime.now(timezone.utc).isoformat()
        doc = {
            "post_id": post_id,
            "author": payload.author,
            "content": payload.content,
            "created_at": created_at,
        }
        result = collection.insert_one(doc)
        comment = CommentRead(id=str(result.inserted_id), **doc)
        self._emit_event("post.commented", comment.model_dump())
        return comment

    def update_post(self, post_id: str, payload: PostUpdate) -> PostRead:
        self._ensure_ready()
        self._publish_command("forum.update_post", {"post_id": post_id, **payload.model_dump(exclude_unset=True)})
        collection = self._collection()
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return self.get_post(post_id)
        result = collection.find_one_and_update(
            {"_id": self._to_object_id(post_id)},
            {"$set": updates},
            return_document=True,
        )
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="post not found")
        post = self._to_read(result)
        self._emit_event("post.updated", post.model_dump())
        return post

    def delete_post(self, post_id: str) -> bool:
        self._ensure_ready()
        self._publish_command("forum.delete_post", {"post_id": post_id})
        collection = self._collection()
        result = collection.delete_one({"_id": self._to_object_id(post_id)})
        deleted = result.deleted_count == 1
        if deleted:
            self._emit_event("post.deleted", {"id": post_id})
        return deleted

    def _ensure_ready(self) -> None:
        if not self._mongo:
            self._init_mongo()

    def _collection(self):
        return self._mongo[self.mongo_db][self.mongo_collection]

    def _init_mongo(self) -> None:
        try:
            self._mongo = MongoClient(self.mongo_uri)
            self._mongo.admin.command("ping")
        except Exception as exc:
            logger.exception("Mongo init failed: %s", exc)
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
                group_id="forum-service",
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

    def _to_object_id(self, post_id: str) -> ObjectId:
        try:
            return ObjectId(post_id)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid post id") from exc

    def _to_read(self, doc: dict) -> PostRead:
        return PostRead(
            id=str(doc["_id"]),
            title=doc["title"],
            content=doc["content"],
            author=doc["author"],
            created_at=doc["created_at"],
        )


forum_service = ForumService()
