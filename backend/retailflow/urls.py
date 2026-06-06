from django.contrib import admin
from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def healthcheck(_request):
    return Response({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", healthcheck, name="healthcheck"),
    path("api/orders/", include("apps.orders.urls")),
    path("api/inventory/", include("apps.inventory.urls")),
    path("api/events/", include("apps.events.urls")),
]
