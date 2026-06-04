from rest_framework import serializers

from .models import InventoryBalance, Sku, Store, Warehouse


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "code", "name", "city", "is_active", "created_at"]


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "code", "name", "city", "is_active", "created_at"]


class SkuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sku
        fields = ["id", "sku", "name", "reorder_point", "created_at"]


class InventoryBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryBalance
        fields = ["id", "sku", "warehouse", "available_quantity", "reserved_quantity", "updated_at"]

