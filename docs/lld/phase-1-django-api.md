# Phase 1 Low-Level Design: Django API and PostgreSQL

## Apps

- `inventory`: stores, warehouses, SKUs, and inventory balances.
- `orders`: order header and order line write workflow.
- `replenishment`: future recommendation models and scoring tasks.
- `events`: event log and event contract storage.

## Initial Data Model

### Store

- `code`: unique business identifier.
- `name`: display name.
- `city`: operational grouping.
- `is_active`: allows soft operational disablement.

### Warehouse

- `code`: unique business identifier.
- `name`: display name.
- `city`: allocation locality.
- `is_active`: allows disabling a fulfillment point.

### SKU

- `sku`: unique item identifier.
- `name`: display name.
- `reorder_point`: minimum healthy stock threshold.

### InventoryBalance

- `sku`, `warehouse`: unique stock position.
- `available_quantity`: stock available to allocate.
- `reserved_quantity`: stock already reserved.

### Order

- `idempotency_key`: protects against duplicate external retries.
- `store`: requesting store.
- `status`: `created`, `processing`, `allocated`, or `rejected`.

### OrderLine

- `order`: parent order.
- `sku`: requested item.
- `requested_quantity`: demand.
- `allocated_quantity`: fulfillment result.

## API Contract

### Create Order

`POST /api/orders/`

```json
{
  "idempotency_key": "ebd41ddc-0be6-45c2-9c51-b762b51de407",
  "store": 1,
  "lines": [
    {"sku": 1, "requested_quantity": 5}
  ]
}
```

Response:

```json
{
  "id": 1,
  "idempotency_key": "ebd41ddc-0be6-45c2-9c51-b762b51de407",
  "store": 1,
  "status": "created",
  "lines": [
    {"sku": 1, "requested_quantity": 5}
  ],
  "created_at": "2026-06-04T00:00:00Z"
}
```

## Async Flow

1. API validates order payload.
2. API creates order and lines in one transaction.
3. Transaction commit schedules `process_order`.
4. Celery updates order status to `processing`.
5. Debezium captures the order table change and publishes it to Kafka.
6. Kafka consumer reads `retailflow.public.orders_order`.

## Next Implementation Steps

1. Generate migrations.
2. Add seed data command.
3. Add allocation logic in Celery.
4. Add API tests for order creation and idempotency.

