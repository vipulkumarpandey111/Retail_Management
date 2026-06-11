from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .aws_messaging import publish_sns_message, publish_sqs_message
from .kafka import publish_direct_event
from .serializers import (
    AwsSnsPublishSerializer,
    AwsSqsPublishSerializer,
    DirectEventPublishSerializer,
)


class CacheProbeView(APIView):
    def get(self, _request):
        key = "retailflow:infra:cache_probe_count"
        current_count = cache.get(key, 0)
        next_count = int(current_count) + 1
        cache.set(key, next_count, timeout=300)

        return Response(
            {
                "cache_key": key,
                "cache_value": next_count,
                "ttl_seconds": 300,
                "purpose": "Proves Django is reading and writing through Redis cache.",
            }
        )


class DirectEventPublishView(APIView):
    def post(self, request):
        serializer = DirectEventPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = publish_direct_event(**serializer.validated_data)
        return Response(result, status=status.HTTP_202_ACCEPTED)


class AwsConfigProbeView(APIView):
    def get(self, _request):
        return Response(
            {
                "aws_region": settings.AWS_REGION,
                "sqs_configured": bool(settings.AWS_SQS_QUEUE_URL),
                "sns_configured": bool(settings.AWS_SNS_TOPIC_ARN),
                "sqs_queue_url_preview": settings.AWS_SQS_QUEUE_URL[:60]
                if settings.AWS_SQS_QUEUE_URL
                else "",
                "sns_topic_arn_preview": settings.AWS_SNS_TOPIC_ARN[:60]
                if settings.AWS_SNS_TOPIC_ARN
                else "",
                "purpose": (
                    "Confirms whether AWS messaging env vars are wired "
                    "without exposing full secret values."
                ),
            }
        )


class AwsSqsPublishView(APIView):
    def post(self, request):
        serializer = AwsSqsPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = publish_sqs_message(**serializer.validated_data)
        return Response(result, status=status.HTTP_202_ACCEPTED)


class AwsSnsPublishView(APIView):
    def post(self, request):
        serializer = AwsSnsPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = publish_sns_message(**serializer.validated_data)
        return Response(result, status=status.HTTP_202_ACCEPTED)
