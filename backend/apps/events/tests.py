from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.events.kafka import build_partition_key, publish_direct_event


class CacheProbeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def test_cache_probe_increments_value(self):
        first_response = self.client.get("/api/events/cache-probe/")
        second_response = self.client.get("/api/events/cache-probe/")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(first_response.json()["cache_value"], 1)
        self.assertEqual(second_response.json()["cache_value"], 2)


class DirectEventPublishViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("apps.events.views.publish_direct_event")
    def test_direct_publish_returns_accepted(self, publish_direct_event_mock):
        publish_direct_event_mock.return_value = {
            "topic": "retailflow.direct.order_signals",
            "delivery": {"topic": "retailflow.direct.order_signals", "partition": 0, "offset": 12},
            "message": {"event_type": "order.signal.created"},
        }

        response = self.client.post(
            "/api/events/direct-publish/",
            data={
                "event_type": "order.signal.created",
                "payload": {"order_id": 101},
                "partition_key_strategy": "order_id",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        publish_direct_event_mock.assert_called_once()
        self.assertEqual(response.json()["delivery"]["partition"], 0)


class KafkaHelpersTests(TestCase):
    def test_build_partition_key_uses_order_id(self):
        key = build_partition_key(
            event_type="order.signal.created",
            payload={"order_id": 101},
            partition_key_strategy="order_id",
        )

        self.assertEqual(key, "101")

    def test_build_partition_key_requires_custom_key(self):
        with self.assertRaisesMessage(
            ValueError, "custom_key is required when partition_key_strategy is custom"
        ):
            build_partition_key(
                event_type="order.signal.created",
                payload={"order_id": 101},
                partition_key_strategy="custom",
            )

    @patch("apps.events.kafka.Producer")
    def test_publish_direct_event_uses_delivery_metadata(self, producer_cls_mock):
        producer_mock = producer_cls_mock.return_value

        def produce_side_effect(topic, key, value, callback):
            class KafkaMessage:
                def topic(self):
                    return topic

                def partition(self):
                    return 2

                def offset(self):
                    return 34

            callback(None, KafkaMessage())

        producer_mock.produce.side_effect = produce_side_effect

        result = publish_direct_event(
            event_type="order.signal.created",
            payload={"order_id": 101, "store_code": "BLR-001"},
            partition_key_strategy="order_id",
            topic="retailflow.direct.order_signals.partitioned",
        )

        self.assertEqual(result["topic"], "retailflow.direct.order_signals.partitioned")
        self.assertEqual(result["delivery"]["partition"], 2)
        self.assertEqual(result["delivery"]["offset"], 34)
        self.assertEqual(result["message"]["partition_key"], "101")
        producer_mock.flush.assert_called_once_with(10)

