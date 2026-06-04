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
    consumer.subscribe(["retailflow.public.orders_order"])
    try:
        while running:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                print(f"kafka error: {message.error()}")
                continue

            payload = json.loads(message.value().decode("utf-8"))
            print(json.dumps({"topic": message.topic(), "payload": payload}, default=str))
            consumer.commit(message=message)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()

