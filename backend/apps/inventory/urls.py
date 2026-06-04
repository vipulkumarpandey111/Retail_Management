from django.urls import path

from .views import InventoryBalanceListView

urlpatterns = [
    path("balances/", InventoryBalanceListView.as_view(), name="inventory-balance-list"),
]

