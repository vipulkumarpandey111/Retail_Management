import json

from confluent_kafka import Producer
from django.conf import settings


def build_partition_key(event_type, payload, partition_key_strategy, custom_key=None):
    if partition_key_strategy == "event_type":
        return event_type
    if partition_key_strategy == "order_id":
        order_id = payload.get("order_id")
        if order_id is None:
            raise ValueError("payload.order_id is required when partition_key_strategy is order_id")
        return str(order_id)
    if partition_key_strategy == "custom":
        if not custom_key:
            raise ValueError("custom_key is required when partition_key_strategy is custom")
        return custom_key
    raise ValueError(f"Unsupported partition_key_strategy: {partition_key_strategy}")


def publish_direct_event(event_type, payload, partition_key_strategy="event_type", custom_key=None):
    producer = Producer({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})
    partition_key = build_partition_key(event_type, payload, partition_key_strategy, custom_key)
    message = {
        "event_type": event_type,
        "payload": payload,
        "source": "django-api-direct-producer",
        "partition_key_strategy": partition_key_strategy,
        "partition_key": partition_key,
    }
    delivery = {}

    def delivery_report(error, kafka_message):
        if error is not None:
            delivery["error"] = str(error)
            return
        delivery.update(
            {
                "topic": kafka_message.topic(),
                "partition": kafka_message.partition(),
                "offset": kafka_message.offset(),
            }
        )

    producer.produce(
        settings.KAFKA_DIRECT_TOPIC,
        key=partition_key,
        value=json.dumps(message, default=str).encode("utf-8"),
        callback=delivery_report,
    )
    producer.flush(10)
    if "error" in delivery:
        raise RuntimeError(f"Kafka delivery failed: {delivery['error']}")
    return {"topic": settings.KAFKA_DIRECT_TOPIC, "delivery": delivery, "message": message}
