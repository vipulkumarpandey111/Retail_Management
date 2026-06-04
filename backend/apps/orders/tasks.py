from celery import shared_task


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_order(self, order_id):
    from .models import Order

    order = Order.objects.get(id=order_id)
    order.status = Order.Status.PROCESSING
    order.save(update_fields=["status", "updated_at"])
    return {"order_id": order_id, "status": order.status}

