import json
import os
import signal

from confluent_kafka import Consumer
from dotenv import load_dotenv

load_dotenv()

running = True


def stop(_signum, _frame):
    global running
    running = False


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)


def classify_topic(topic):
    if topic.startswith("retailflow.public."):
        return "debezium_cdc"
    if topic.startswith("retailflow.direct."):
        return "direct_app_event"
    return "unknown"


def summarize_direct_event(payload):
    return {
        "event_type": payload.get("event_type"),
        "source": payload.get("source"),
        "partition_key_strategy": payload.get("partition_key_strategy"),
        "partition_key": payload.get("partition_key"),
        "payload_keys": sorted(payload.get("payload", {}).keys()),
    }


def summarize_cdc_event(payload):
    after = payload.get("after") or {}
    before = payload.get("before") or {}
    source = payload.get("source") or {}

    return {
        "operation": payload.get("op"),
        "table": source.get("table"),
        "schema": source.get("schema"),
        "aggregate_id": after.get("id") or before.get("id"),
        "before_keys": sorted(before.keys()),
        "after_keys": sorted(after.keys()),
    }


def build_message_output(message, payload):
    topic = message.topic()
    classification = classify_topic(topic)
    output = {
        "consumer_group": os.getenv("KAFKA_GROUP_ID", "retailflow-order-consumer"),
        "consumer_name": os.getenv("KAFKA_CONSUMER_NAME", "consumer-1"),
        "classification": classification,
        "topic": topic,
        "partition": message.partition(),
        "offset": message.offset(),
        "key": message.key().decode("utf-8") if message.key() else None,
    }

    if classification == "direct_app_event":
        output["summary"] = summarize_direct_event(payload)
    elif classification == "debezium_cdc":
        output["summary"] = summarize_cdc_event(payload)
    else:
        output["summary"] = {"message": "Unknown topic classification"}

    output["payload"] = payload
    return output


def build_consumer():
    return Consumer(
        {
            "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            "group.id": os.getenv("KAFKA_GROUP_ID", "retailflow-order-consumer"),
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )


def main():
    consumer = build_consumer()
    topics = [
        topic.strip()
        for topic in os.getenv(
            "KAFKA_CONSUMER_TOPICS",
            (
                "retailflow.public.orders_order,"
                "retailflow.direct.order_signals,"
                "retailflow.direct.order_signals.partitioned"
            ),
        ).split(",")
        if topic.strip()
    ]
    consumer.subscribe(topics)
    print(f"Subscribed to Kafka topics: {topics}")
    try:
        while running:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                print(f"kafka error: {message.error()}")
                continue

            payload = json.loads(message.value().decode("utf-8"))
            print(json.dumps(build_message_output(message, payload), default=str))
            consumer.commit(message=message)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
