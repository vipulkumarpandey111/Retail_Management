from django.urls import path

from .views import CacheProbeView, DirectEventPublishView

urlpatterns = [
    path("cache-probe/", CacheProbeView.as_view(), name="cache-probe"),
    path("direct-publish/", DirectEventPublishView.as_view(), name="direct-event-publish"),
]

