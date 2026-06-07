from rest_framework import serializers


class DirectEventPublishSerializer(serializers.Serializer):
    class PartitionKeyStrategy:
        EVENT_TYPE = "event_type"
        ORDER_ID = "order_id"
        CUSTOM = "custom"

    event_type = serializers.CharField(max_length=120)
    topic = serializers.CharField(max_length=200, required=False, allow_blank=True)
    payload = serializers.JSONField(default=dict)
    partition_key_strategy = serializers.ChoiceField(
        choices=[
            PartitionKeyStrategy.EVENT_TYPE,
            PartitionKeyStrategy.ORDER_ID,
            PartitionKeyStrategy.CUSTOM,
        ],
        default=PartitionKeyStrategy.EVENT_TYPE,
    )
    custom_key = serializers.CharField(max_length=160, required=False, allow_blank=True)
