from rest_framework import serializers


class DirectEventPublishSerializer(serializers.Serializer):
    event_type = serializers.CharField(max_length=120)
    payload = serializers.JSONField(default=dict)

