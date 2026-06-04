import uuid

from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PROCESSING = "processing", "Processing"
        ALLOCATED = "allocated", "Allocated"
        REJECTED = "rejected", "Rejected"

    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True)
    store = models.ForeignKey("inventory.Store", on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.CREATED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} - {self.status}"


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    sku = models.ForeignKey("inventory.Sku", on_delete=models.PROTECT, related_name="order_lines")
    requested_quantity = models.PositiveIntegerField()
    allocated_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "sku"], name="uniq_order_line_sku")
        ]

