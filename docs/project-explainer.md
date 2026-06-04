# RetailFlow Lab Project Explainer

This document explains the current project from the top down. The goal is to make the infrastructure, setup flow, business flow, and moving parts understandable before we add more features.

## 1. Current Project State

RetailFlow Lab is currently a local event-driven backend system.

At this stage, it can:

- Run PostgreSQL, Redis, Kafka, Zookeeper, and Kafka Connect with Debezium through Docker Compose.
- Run a Django REST API locally.
- Persist retail data in PostgreSQL.
- Create orders through an API endpoint.
- Trigger a Celery task through Redis after an order is committed.
- Update the order status asynchronously.
- Stream PostgreSQL table changes into Kafka through Debezium CDC.
- Run a Python Kafka consumer that reads the Debezium-generated order topic.

The current project is intentionally local-first. AWS, Kubernetes, and CI/CD are planned, but not yet the active runtime path.

## 2. Big Picture Runtime Flow

```mermaid
flowchart LR
    Client["API Client / PowerShell"] --> API["Django REST API"]
    API --> PG["PostgreSQL"]
    API --> Redis["Redis"]
    Redis --> Celery["Celery Worker"]
    Celery --> PG
    PG --> Debezium["Kafka Connect + Debezium"]
    Debezium --> Kafka["Kafka Topic"]
    Kafka --> Consumer["Python Kafka Consumer"]
```

In plain English:

1. You call the Django API.
2. Django writes business data into PostgreSQL.
3. Django schedules async work through Celery.
4. Redis acts as the Celery message broker.
5. Celery picks up the task and updates the order.
6. Debezium watches PostgreSQL committed changes.
7. Debezium publishes those changes into Kafka.
8. The Kafka consumer reads the order-change topic.

## 3. Repository Layout

The important folders right now are:

```text
backend/
  manage.py
  retailflow/
    settings.py
    celery.py
    urls.py
  apps/
    inventory/
    orders/
    replenishment/
    events/

infra/
  docker-compose/
    docker-compose.local.yml
    debezium-postgres.json

workers/
  kafka_consumer/
    main.py

docs/
  design/
  lld/
  project-explainer.md

scripts/
  local/

.github/
  workflows/
```

How to read this structure:

- `backend/` is the main Django service.
- `backend/apps/` contains domain modules.
- `infra/docker-compose/` contains local infrastructure containers.
- `workers/kafka_consumer/` contains the standalone Kafka consumer.
- `docs/` contains explanation and design documentation.
- `.github/workflows/` contains early CI/CD workflow placeholders.

## 4. Infrastructure Components

### PostgreSQL

PostgreSQL is the source of truth.

It stores:

- Stores
- Warehouses
- SKUs
- Inventory balances
- Orders
- Order lines
- Event logs

Configured in:

```text
infra/docker-compose/docker-compose.local.yml
backend/retailflow/settings.py
.env
.env.example
```

Important Docker Compose config:

```yaml
postgres:
  image: postgres:16
  container_name: retailflow-postgres
  ports:
    - "5433:5432"
```

Why `5433:5432`?

- `5432` is the port inside the container.
- `5433` is the port exposed on your laptop.
- This avoids conflict with another local PostgreSQL already using `5432`.

Important CDC config:

```yaml
command:
  - postgres
  - -c
  - wal_level=logical
  - -c
  - max_wal_senders=10
  - -c
  - max_replication_slots=10
```

This enables logical replication, which Debezium needs to read committed database changes.

### Redis

Redis is currently used as the Celery broker and result backend.

Configured in:

```text
infra/docker-compose/docker-compose.local.yml
backend/retailflow/settings.py
```

Important settings:

```python
CELERY_BROKER_URL = redis://localhost:6379/0
CELERY_RESULT_BACKEND = redis://localhost:6379/1
```

Role in the flow:

- Django creates a Celery task message.
- Redis stores that message.
- Celery worker consumes the message.
- Celery executes the background job.

### Celery

Celery handles async work outside the API request path.

Configured in:

```text
backend/retailflow/celery.py
backend/retailflow/__init__.py
backend/retailflow/settings.py
backend/apps/orders/tasks.py
```

The project-level Celery app is:

```text
backend/retailflow/celery.py
```

The current business task is:

```text
backend/apps/orders/tasks.py
```

Current task responsibility:

- Load an order by ID.
- Mark it as `processing`.
- Save the order.

Current Celery annotation:

```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
```

Meaning:

- `shared_task`: makes this function a Celery task.
- `bind=True`: gives access to the task instance as `self`.
- `autoretry_for=(Exception,)`: retry if an exception happens.
- `retry_backoff=True`: wait progressively longer between retries.
- `max_retries=3`: retry up to three times.

### Kafka

Kafka is the event streaming layer.

Configured in:

```text
infra/docker-compose/docker-compose.local.yml
```

Important config:

```yaml
kafka:
  image: confluentinc/cp-kafka:7.6.1
  ports:
    - "9092:9092"
  environment:
    KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
```

Why two listeners?

- `kafka:29092` is used by other containers in the Docker network.
- `localhost:9092` is used by programs running on your laptop, like `workers/kafka_consumer/main.py`.

Kafka topic currently used by the consumer:

```text
retailflow.public.orders_order
```

This topic is created by Debezium when it sees changes to the `orders_order` table.

### Zookeeper

Zookeeper supports this Confluent Kafka image.

Configured in:

```text
infra/docker-compose/docker-compose.local.yml
```

It is not business-facing. It exists because this Kafka image uses Zookeeper for broker coordination.

### Kafka Connect

Kafka Connect runs connectors that move data into or out of Kafka.

Configured in:

```text
infra/docker-compose/docker-compose.local.yml
```

Important config:

```yaml
kafka-connect:
  image: debezium/connect:2.7.0.Final
  ports:
    - "8083:8083"
  environment:
    BOOTSTRAP_SERVERS: kafka:29092
    GROUP_ID: retailflow-connect
    CONFIG_STORAGE_TOPIC: retailflow_connect_configs
    OFFSET_STORAGE_TOPIC: retailflow_connect_offsets
    STATUS_STORAGE_TOPIC: retailflow_connect_status
```

Kafka Connect exposes an HTTP API at:

```text
http://localhost:8083
```

You use that API to register the Debezium connector.

### Debezium CDC

Debezium reads database changes from PostgreSQL and publishes them to Kafka.

Configured in:

```text
infra/docker-compose/debezium-postgres.json
```

Important connector config:

```json
{
  "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
  "database.hostname": "postgres",
  "database.port": "5432",
  "topic.prefix": "retailflow",
  "plugin.name": "pgoutput",
  "slot.name": "retailflow_debezium",
  "publication.autocreate.mode": "filtered",
  "table.include.list": "public.orders_order,public.orders_orderline,public.inventory_inventorybalance"
}
```

Important meanings:

- `connector.class`: tells Kafka Connect to run the Debezium PostgreSQL connector.
- `database.hostname`: uses Docker service name `postgres`, not `localhost`.
- `database.port`: uses container-internal PostgreSQL port `5432`.
- `topic.prefix`: all Debezium topics start with `retailflow`.
- `plugin.name`: uses PostgreSQL `pgoutput` logical decoding.
- `slot.name`: PostgreSQL replication slot used by Debezium.
- `publication.autocreate.mode`: Debezium creates a filtered publication for selected tables.
- `table.include.list`: only these tables are streamed.

Current streamed tables:

- `public.orders_order`
- `public.orders_orderline`
- `public.inventory_inventorybalance`

Current important topic:

```text
retailflow.public.orders_order
```

## 5. Business Domain

The project models a retail inventory and replenishment backend.

Current business entities:

- Store: a retail store placing demand.
- Warehouse: a fulfillment location holding inventory.
- SKU: a sellable product.
- InventoryBalance: stock position for one SKU in one warehouse.
- Order: demand from a store.
- OrderLine: requested SKU and quantity inside an order.
- EventLog: placeholder for future event auditing.

## 6. Current Business Flow

The implemented flow is intentionally small but end-to-end.

### Order Creation Flow

1. API client sends an order request.
2. `OrderCreateView` receives the request.
3. `OrderCreateSerializer` validates and creates the order.
4. The serializer creates `Order` and `OrderLine` records in one database transaction.
5. After the transaction commits, Django schedules `process_order.delay(order.id)`.
6. Celery worker picks up the task from Redis.
7. Celery updates order status from `created` to `processing`.
8. PostgreSQL records the insert and update.
9. Debezium reads those committed table changes.
10. Debezium publishes change events to Kafka.
11. Kafka consumer reads the order topic and prints the event.

### Why `transaction.on_commit` Matters

The Celery task is scheduled only after the database transaction commits.

That prevents this bad timing problem:

- API creates order inside transaction.
- Celery starts too early.
- Celery tries to read an order that is not committed yet.

So the current design says: first commit data, then schedule async work.

## 7. Module Responsibilities

### `backend/apps/inventory/models.py`

Owns inventory-side domain objects:

- `Store`
- `Warehouse`
- `Sku`
- `InventoryBalance`

Current responsibility:

- Represent stock and fulfillment data.
- Provide data needed by order creation and future allocation logic.

### `backend/apps/orders/models.py`

Owns order-side domain objects:

- `Order`
- `OrderLine`

Current responsibility:

- Represent customer/store demand.
- Track order status.
- Store requested and allocated quantities.

### `backend/apps/orders/serializers.py`

Owns the current order write workflow.

Current responsibility:

- Validate incoming order payloads.
- Create `Order`.
- Create child `OrderLine` records.
- Schedule Celery task after commit.

This is currently the central business-flow file.

### `backend/apps/orders/tasks.py`

Owns async order processing.

Current responsibility:

- Receive order ID from Celery.
- Update order status to `processing`.

Future responsibility:

- Reserve stock.
- Allocate warehouse inventory.
- Reject orders if stock is not available.
- Emit notification/report events.

### `backend/retailflow/settings.py`

Owns application configuration.

Current responsibility:

- Read `.env`.
- Configure PostgreSQL.
- Configure Django REST Framework.
- Configure Celery broker/result backend.

### `backend/retailflow/celery.py`

Owns Celery application bootstrapping.

Current responsibility:

- Create Celery app.
- Load settings from Django settings.
- Auto-discover `tasks.py` files inside installed Django apps.

### `workers/kafka_consumer/main.py`

Owns Kafka consumption outside Django.

Current responsibility:

- Connect to Kafka at `localhost:9092`.
- Subscribe to `retailflow.public.orders_order`.
- Poll messages.
- Print the Debezium payload.
- Commit offsets manually after processing.

## 8. Config Files To Study First

Read these in this order:

1. `infra/docker-compose/docker-compose.local.yml`
2. `.env.example`
3. `backend/retailflow/settings.py`
4. `backend/retailflow/celery.py`
5. `backend/apps/orders/serializers.py`
6. `backend/apps/orders/tasks.py`
7. `infra/docker-compose/debezium-postgres.json`
8. `workers/kafka_consumer/main.py`

This order mirrors the real runtime flow:

Infrastructure -> environment -> Django config -> business write -> async task -> CDC -> event consumer.

## 9. Commands Run So Far

### Create Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install Dependencies

```powershell
.\.venv\Scripts\python -m pip install -r backend\requirements\dev.txt
```

### Generate Migrations

```powershell
.\.venv\Scripts\python backend\manage.py makemigrations inventory orders events replenishment
```

### Validate Django Project

```powershell
.\.venv\Scripts\python backend\manage.py check
```

### Validate Linting

```powershell
.\.venv\Scripts\ruff check backend workers
```

### Validate Docker Compose

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml config
```

### Start PostgreSQL And Redis

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml up -d postgres redis
```

### Run Migrations

```powershell
.\.venv\Scripts\python backend\manage.py migrate
```

### Start Django API

```powershell
.\.venv\Scripts\python backend\manage.py runserver
```

### Start Celery Worker

Run from the `backend` directory:

```powershell
C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\.venv\Scripts\celery -A retailflow worker -l info
```

### Start Kafka Stack

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml up -d zookeeper kafka kafka-connect
```

### Register Debezium Connector

PowerShell version:

```powershell
$connectorConfig = Get-Content -Raw "infra\docker-compose\debezium-postgres.json"

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8083/connectors" `
  -ContentType "application/json" `
  -Body $connectorConfig
```

### Check Kafka Connect Connectors

```powershell
Invoke-RestMethod "http://localhost:8083/connectors"
```

### Check Debezium Connector Status

```powershell
Invoke-RestMethod "http://localhost:8083/connectors/retailflow-postgres-connector/status"
```

### Start Kafka Consumer

```powershell
.\.venv\Scripts\python workers\kafka_consumer\main.py
```

## 10. Useful Verification Commands

### Docker Containers

```powershell
docker ps
```

### Container Logs

```powershell
docker logs retailflow-postgres
docker logs retailflow-redis
docker logs retailflow-kafka
docker logs retailflow-kafka-connect
```

### Stop Containers Without Deleting Data

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml down
```

### Stop Containers And Delete PostgreSQL Volume

Only use this when you want a fresh local database.

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml down -v
```

### Health Check API

```powershell
Invoke-RestMethod "http://localhost:8000/health/"
```

### Inventory API

```powershell
Invoke-RestMethod "http://localhost:8000/api/inventory/balances/"
```

### Create Order

```powershell
$body = @{
  store = 1
  lines = @(
    @{
      sku = 1
      requested_quantity = 3
    }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/orders/" `
  -ContentType "application/json" `
  -Body $body
```

### Read Order

```powershell
Invoke-RestMethod "http://localhost:8000/api/orders/1/"
```

## 11. Kafka And Debezium Syntax To Understand

### Kafka Consumer Config

In `workers/kafka_consumer/main.py`:

```python
{
    "bootstrap.servers": "localhost:9092",
    "group.id": "retailflow-order-consumer",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
}
```

Meaning:

- `bootstrap.servers`: Kafka address used by this process.
- `group.id`: consumer group name.
- `auto.offset.reset`: start from earliest available event if no offset exists.
- `enable.auto.commit`: disabled so the code commits only after processing.

### Topic Subscription

```python
consumer.subscribe(["retailflow.public.orders_order"])
```

Meaning:

- The consumer listens to one Debezium-created topic.
- Topic name follows `topic.prefix.schema.table`.

### Polling Messages

```python
message = consumer.poll(1.0)
```

Meaning:

- Wait up to one second for a Kafka message.
- If no message arrives, loop again.

### Manual Offset Commit

```python
consumer.commit(message=message)
```

Meaning:

- The consumer records that this message has been handled.
- In production, this should happen after real processing succeeds.

### Debezium Connector Registration

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8083/connectors" `
  -ContentType "application/json" `
  -Body $connectorConfig
```

Meaning:

- You are calling Kafka Connect's REST API.
- Kafka Connect reads the JSON body.
- It starts a Debezium connector task.
- Debezium begins reading PostgreSQL changes.

## 12. Docker Compose Management

Docker Compose is currently the local infrastructure controller.

The main file:

```text
infra/docker-compose/docker-compose.local.yml
```

Start selected services:

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml up -d postgres redis
```

Start all infrastructure services:

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml up -d
```

Recreate a service after config changes:

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml up -d --force-recreate postgres
```

See service status:

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml ps
```

Read logs:

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml logs kafka-connect
```

## 13. Current Limitations

The current implementation is a working learning milestone, not the finished product.

Current limitations:

- Order processing only moves status to `processing`.
- No real inventory allocation yet.
- No idempotency lookup behavior yet, even though the field exists.
- No automated seed command yet.
- Kafka consumer only prints events.
- No SQS/SNS/S3/Lambda integration yet.
- No Dockerfile for the Django app yet.
- No Kubernetes manifests implemented yet.
- CI exists as an early skeleton, but the folder is not yet initialized as a Git repository.

## 14. Next Recommended Steps

The next steps should build on the local loop you already verified.

### Step 1: Add Seed Command

Create a repeatable Django management command that inserts a store, warehouse, SKU, and inventory balance.

Why:

- Avoid manual shell setup.
- Make tests and demos repeatable.

### Step 2: Implement Real Allocation Logic

Update Celery order processing so it:

- Reads requested order lines.
- Finds available inventory.
- Reserves stock.
- Sets order to `allocated` or `rejected`.

Why:

- This turns the project from infrastructure demo into business logic.

### Step 3: Add Tests

Add tests for:

- Order creation.
- Async task behavior.
- Inventory reservation.
- Duplicate idempotency key behavior.

Why:

- This prepares the project for CI/CD.

### Step 4: Improve Kafka Consumer Behavior

Move from printing events to meaningful processing.

Possible behavior:

- Store consumed events.
- Publish selected events to SQS later.
- Call an internal API endpoint later.
- Add retry and dead-letter behavior.

### Step 5: Dockerize Application Services

Add Dockerfiles for:

- Django API.
- Celery worker.
- Kafka consumer.

Why:

- Required before Docker Compose EC2 deployment and Kubernetes.

### Step 6: Add Local Kubernetes Manifests

Use Docker Desktop Kubernetes for:

- API deployment.
- Celery worker deployment.
- Kafka consumer deployment.
- Redis deployment.
- ConfigMaps and Secrets.

PostgreSQL can initially remain local/Compose or run as a simple local Kubernetes workload for learning.

### Step 7: Add AWS Free-Tier Integrations

Add carefully:

- S3 for tiny report files.
- SQS for low-volume event queueing.
- SNS for notification fan-out.
- Lambda for lightweight SQS processing.
- Optional RDS PostgreSQL only after Free Tier eligibility is confirmed.

## 15. Mental Model To Keep

Think of this project in layers:

```text
Business API
  Django REST endpoint creates orders.

Transaction Store
  PostgreSQL stores the truth.

Async Work
  Celery + Redis handle slow/background processing.

Change Data Capture
  Debezium watches committed PostgreSQL changes.

Event Streaming
  Kafka transports those changes as events.

Consumers
  Worker services react to events.

Deployment
  Docker Compose locally first, Kubernetes locally next, EC2 Docker Compose later.
```

That is the backbone of the project. Every future phase should attach cleanly to one of these layers.

