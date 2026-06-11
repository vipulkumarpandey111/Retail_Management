from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient

from apps.events.kafka import build_partition_key, publish_direct_event


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "retailflow-events-tests",
        }
    }
)
class CacheProbeViewTests(SimpleTestCase):
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


class DirectEventPublishViewTests(SimpleTestCase):
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

    @patch("apps.events.views.publish_direct_event")
    def test_direct_publish_accepts_producer_id(self, publish_direct_event_mock):
        publish_direct_event_mock.return_value = {
            "topic": "retailflow.direct.order_signals.partitioned",
            "delivery": {
                "topic": "retailflow.direct.order_signals.partitioned",
                "partition": 1,
                "offset": 7,
            },
            "message": {"event_type": "order.signal.created", "source": "producer-a"},
        }

        response = self.client.post(
            "/api/events/direct-publish/",
            data={
                "event_type": "order.signal.created",
                "payload": {"order_id": 101},
                "partition_key_strategy": "order_id",
                "producer_id": "producer-a",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        publish_direct_event_mock.assert_called_once()
        self.assertEqual(response.json()["message"]["source"], "producer-a")


class AwsMessagingViewTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_aws_config_probe_reports_configuration_presence(self):
        response = self.client.get("/api/events/aws-config-probe/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("aws_region", response.json())
        self.assertIn("sqs_configured", response.json())
        self.assertIn("sns_configured", response.json())

    @patch("apps.events.views.publish_sqs_message")
    def test_aws_sqs_publish_returns_accepted(self, publish_sqs_message_mock):
        publish_sqs_message_mock.return_value = {
            "queue_url": "https://sqs.ap-south-1.amazonaws.com/123456789012/retailflow-demo",
            "message_id": "mid-123",
            "md5_of_body": "md5-123",
            "message_group_id": "",
            "message": {"event_type": "order.signal.created"},
        }

        response = self.client.post(
            "/api/events/aws-sqs-publish/",
            data={
                "event_type": "order.signal.created",
                "payload": {"order_id": 101},
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        publish_sqs_message_mock.assert_called_once()
        self.assertEqual(response.json()["message_id"], "mid-123")

    @patch("apps.events.views.publish_sns_message")
    def test_aws_sns_publish_returns_accepted(self, publish_sns_message_mock):
        publish_sns_message_mock.return_value = {
            "topic_arn": "arn:aws:sns:ap-south-1:123456789012:retailflow-demo",
            "message_id": "sns-123",
            "subject": "order.signal.created",
            "message": {"event_type": "order.signal.created"},
        }

        response = self.client.post(
            "/api/events/aws-sns-publish/",
            data={
                "event_type": "order.signal.created",
                "payload": {"order_id": 101},
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        publish_sns_message_mock.assert_called_once()
        self.assertEqual(response.json()["message_id"], "sns-123")


class KafkaHelpersTests(SimpleTestCase):
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

    @patch("apps.events.kafka.Producer")
    def test_publish_direct_event_uses_producer_id_as_source(self, producer_cls_mock):
        producer_mock = producer_cls_mock.return_value

        def produce_side_effect(topic, key, value, callback):
            class KafkaMessage:
                def topic(self):
                    return topic

                def partition(self):
                    return 1

                def offset(self):
                    return 8

            callback(None, KafkaMessage())

        producer_mock.produce.side_effect = produce_side_effect

        result = publish_direct_event(
            event_type="order.signal.created",
            payload={"order_id": 101},
            partition_key_strategy="order_id",
            producer_id="producer-a",
            topic="retailflow.direct.order_signals.partitioned",
        )

        self.assertEqual(result["message"]["source"], "producer-a")
