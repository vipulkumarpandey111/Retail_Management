from rest_framework import serializers


class DirectEventPublishSerializer(serializers.Serializer):
    class PartitionKeyStrategy:
        EVENT_TYPE = "event_type"
        ORDER_ID = "order_id"
        CUSTOM = "custom"

    event_type = serializers.CharField(max_length=120)
    topic = serializers.CharField(max_length=200, required=False, allow_blank=True)
    payload = serializers.JSONField(default=dict)
    producer_id = serializers.CharField(max_length=120, required=False, allow_blank=True)
    partition_key_strategy = serializers.ChoiceField(
        choices=[
            PartitionKeyStrategy.EVENT_TYPE,
            PartitionKeyStrategy.ORDER_ID,
            PartitionKeyStrategy.CUSTOM,
        ],
        default=PartitionKeyStrategy.EVENT_TYPE,
    )
    custom_key = serializers.CharField(max_length=160, required=False, allow_blank=True)


class AwsSqsPublishSerializer(serializers.Serializer):
    event_type = serializers.CharField(max_length=120)
    payload = serializers.JSONField(default=dict)
    queue_url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    message_group_id = serializers.CharField(max_length=128, required=False, allow_blank=True)


class AwsSnsPublishSerializer(serializers.Serializer):
    event_type = serializers.CharField(max_length=120)
    payload = serializers.JSONField(default=dict)
    topic_arn = serializers.CharField(max_length=500, required=False, allow_blank=True)
    subject = serializers.CharField(max_length=100, required=False, allow_blank=True)
