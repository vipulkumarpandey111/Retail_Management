from django.urls import path

from .views import (
    AwsConfigProbeView,
    AwsSnsPublishView,
    AwsSqsPublishView,
    CacheProbeView,
    DirectEventPublishView,
)

urlpatterns = [
    path("cache-probe/", CacheProbeView.as_view(), name="cache-probe"),
    path("direct-publish/", DirectEventPublishView.as_view(), name="direct-event-publish"),
    path("aws-config-probe/", AwsConfigProbeView.as_view(), name="aws-config-probe"),
    path("aws-sqs-publish/", AwsSqsPublishView.as_view(), name="aws-sqs-publish"),
    path("aws-sns-publish/", AwsSnsPublishView.as_view(), name="aws-sns-publish"),
]
