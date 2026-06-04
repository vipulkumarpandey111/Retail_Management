from rest_framework.generics import ListAPIView

from .models import InventoryBalance
from .serializers import InventoryBalanceSerializer


class InventoryBalanceListView(ListAPIView):
    queryset = InventoryBalance.objects.select_related("sku", "warehouse").all()
    serializer_class = InventoryBalanceSerializer

