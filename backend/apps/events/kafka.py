import json

from confluent_kafka import Producer
from django.conf import settings


def publish_direct_event(event_type, payload):
    producer = Producer({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})
    message = {
        "event_type": event_type,
        "payload": payload,
        "source": "django-api-direct-producer",
    }
    producer.produce(
        settings.KAFKA_DIRECT_TOPIC,
        key=event_type,
        value=json.dumps(message, default=str).encode("utf-8"),
    )
    producer.flush(10)
    return {"topic": settings.KAFKA_DIRECT_TOPIC, "message": message}

