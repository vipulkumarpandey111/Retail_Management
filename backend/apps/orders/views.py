from rest_framework.generics import CreateAPIView, RetrieveAPIView

from .models import Order
from .serializers import OrderCreateSerializer, OrderSerializer


class OrderCreateView(CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer


class OrderDetailView(RetrieveAPIView):
    queryset = Order.objects.prefetch_related("lines").all()
    serializer_class = OrderSerializer

