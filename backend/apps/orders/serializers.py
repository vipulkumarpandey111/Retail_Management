from django.db import transaction
from rest_framework import serializers

from .models import Order, OrderLine
from .tasks import process_order


class OrderLineCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = ["sku", "requested_quantity"]


class OrderCreateSerializer(serializers.ModelSerializer):
    lines = OrderLineCreateSerializer(many=True)

    class Meta:
        model = Order
        fields = ["id", "idempotency_key", "store", "status", "lines", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def create(self, validated_data):
        lines_data = validated_data.pop("lines")
        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            OrderLine.objects.bulk_create(
                OrderLine(order=order, **line_data) for line_data in lines_data
            )
            transaction.on_commit(lambda: process_order.delay(order.id))
        return order


class OrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = ["id", "sku", "requested_quantity", "allocated_quantity"]


class OrderSerializer(serializers.ModelSerializer):
    lines = OrderLineSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "idempotency_key", "store", "status", "lines", "created_at", "updated_at"]

