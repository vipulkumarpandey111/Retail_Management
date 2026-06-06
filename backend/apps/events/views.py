from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .kafka import publish_direct_event
from .serializers import DirectEventPublishSerializer


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

