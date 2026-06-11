# Running RetailFlow Lab End To End

This is the canonical step-by-step runbook for starting and verifying the project locally. Keep this file updated whenever infrastructure, ports, services, scripts, or run commands change.

## 1. Prerequisites

Install or confirm:

- Docker Desktop is running with Linux containers.
- Python virtual environment exists at `.venv`.
- Project dependencies are installed.
- PowerShell terminal is opened at the project root.

Project root:

```powershell
cd C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn
```

Activate virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

If activation is blocked, use the Python executable directly:

```powershell
.\.venv\Scripts\python --version
```

## 2. Environment File

Create `.env` if it does not exist:

```powershell
Copy-Item .env.example .env
```

Important local values:

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_URL=redis://localhost:6379/2
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_DIRECT_TOPIC=retailflow.direct.order_signals
KAFKA_PARTITION_DEMO_TOPIC=retailflow.direct.order_signals.partitioned
KAFKA_CONSUMER_TOPICS=retailflow.public.orders_order,retailflow.direct.order_signals,retailflow.direct.order_signals.partitioned
AWS_REGION=ap-south-1
AWS_SQS_QUEUE_URL=
AWS_SNS_TOPIC_ARN=
```

PostgreSQL uses host port `5433` to avoid conflict with any local database already using `5432`.

## 3. Start Local Infrastructure

Start PostgreSQL and Redis:

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml up -d postgres redis
```

Start Kafka, Zookeeper, and Kafka Connect:

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml up -d zookeeper kafka kafka-connect
```

Check containers:

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml ps
```

## 3A. Start Full Containerized App Stack

This is the preferred path when you want the API, Celery worker, and Kafka consumer to run as containers instead of separate local terminals.

Build and start everything:

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml up -d --build
```

This starts:

- `retailflow-api`
- `retailflow-celery-worker`
- `retailflow-postgres`
- `retailflow-redis`
- `retailflow-zookeeper`
- `retailflow-kafka`
- `retailflow-kafka-connect`
- `retailflow-kafka-consumer`

When using this path:

- The API runs on `http://localhost:8000`
- Django connects to `postgres:5432` inside Docker
- Celery uses `redis:6379` inside Docker
- Kafka clients use `kafka:29092` inside Docker

## 4. Database Setup

Run migrations:

```powershell
.\.venv\Scripts\python backend\manage.py migrate
```

Optional manual seed data:

```powershell
.\.venv\Scripts\python backend\manage.py shell
```

Paste:

```python
from apps.inventory.models import Store, Warehouse, Sku, InventoryBalance

store, _ = Store.objects.get_or_create(
    code="BLR-001",
    defaults={"name": "Bengaluru Store", "city": "Bengaluru"},
)
warehouse, _ = Warehouse.objects.get_or_create(
    code="WH-BLR",
    defaults={"name": "Bengaluru Warehouse", "city": "Bengaluru"},
)
sku, _ = Sku.objects.get_or_create(
    sku="SKU-IPHONE-15",
    defaults={"name": "iPhone 15", "reorder_point": 5},
)
InventoryBalance.objects.get_or_create(
    sku=sku,
    warehouse=warehouse,
    defaults={"available_quantity": 20},
)
print(store.id, warehouse.id, sku.id)
```

Exit:

```python
exit()
```

## 5. Start Django API

Use this section only if you are running the API directly on your laptop instead of the full containerized app stack.

In terminal 1:

```powershell
.\.venv\Scripts\python backend\manage.py runserver
```

Verify health:

```powershell
Invoke-RestMethod "http://localhost:8000/health/"
```

Expected:

```json
{"status":"ok"}
```

## 6. Start Celery Worker

Use this section only if you are running Celery directly on your laptop instead of the full containerized app stack.

In terminal 2:

```powershell
cd C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\backend
C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\.venv\Scripts\celery -A retailflow worker -l info
```

Celery uses Redis DB `0` as broker and Redis DB `1` as result backend.

## 7. Register Debezium Connector

In terminal 3, from project root:

```powershell
$connectorConfig = Get-Content -Raw "infra\docker-compose\debezium-postgres.json"

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8083/connectors" `
  -ContentType "application/json" `
  -Body $connectorConfig
```

If the connector already exists, that is fine.

Verify:

```powershell
Invoke-RestMethod "http://localhost:8083/connectors"
Invoke-RestMethod "http://localhost:8083/connectors/retailflow-postgres-connector/status"
```

The connector and task should be `RUNNING`.

## 8. Kafka Partition Demo Topic

The original direct topic may have been auto-created by Kafka with one partition:

```text
retailflow.direct.order_signals
```

For partition learning, use this separate topic:

```text
retailflow.direct.order_signals.partitioned
```

Create it with three partitions:

```powershell
.\scripts\kafka\create-direct-topic.ps1 retailflow.direct.order_signals.partitioned 3 1
```

Describe it:

```powershell
.\scripts\kafka\describe-topic.ps1 retailflow.direct.order_signals.partitioned
```

Expected: the topic should show `PartitionCount: 3`.

List topics:

```powershell
.\scripts\kafka\list-topics.ps1
```

## 9. Start Kafka Consumer

Use this section only if you are running the Kafka consumer directly on your laptop instead of the full containerized app stack.

In terminal 4, from project root:

```powershell
.\.venv\Scripts\python workers\kafka_consumer\main.py
```

The consumer subscribes to:

```text
retailflow.public.orders_order
retailflow.direct.order_signals
retailflow.direct.order_signals.partitioned
```

It prints:

- classification
- topic
- partition
- offset
- key
- summary
- payload

Classification meanings:

- `debezium_cdc`: message came from the Debezium CDC path.
- `direct_app_event`: message came from the Django direct Kafka producer path.

## 10. Verify Redis Cache

Call the cache probe multiple times:

```powershell
Invoke-RestMethod "http://localhost:8000/api/events/cache-probe/"
```

Expected:

- `cache_value` increases on each call.
- The value is stored in Redis DB `2`.
- The key expires after 300 seconds.

## 11. Publish Direct Kafka Events

### Partition By Event Type

```powershell
$body = @{
  topic = "retailflow.direct.order_signals.partitioned"
  event_type = "order.signal.created"
  partition_key_strategy = "event_type"
  payload = @{
    order_id = 101
    store_code = "BLR-001"
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/events/direct-publish/" `
  -ContentType "application/json" `
  -Body $body
```

### Partition By Order ID

```powershell
$body = @{
  topic = "retailflow.direct.order_signals.partitioned"
  event_type = "order.signal.created"
  partition_key_strategy = "order_id"
  payload = @{
    order_id = 101
    store_code = "BLR-001"
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/events/direct-publish/" `
  -ContentType "application/json" `
  -Body $body
```

### Partition By Custom Key

```powershell
$body = @{
  topic = "retailflow.direct.order_signals.partitioned"
  event_type = "order.signal.created"
  partition_key_strategy = "custom"
  custom_key = "store:BLR-001"
  payload = @{
    order_id = 101
    store_code = "BLR-001"
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/events/direct-publish/" `
  -ContentType "application/json" `
  -Body $body
```

The API response includes Kafka delivery metadata:

```json
{
  "delivery": {
    "topic": "retailflow.direct.order_signals.partitioned",
    "partition": 1,
    "offset": 0
  }
}
```

The exact partition can differ. The important rule is: the same key should map to the same partition while the topic partition count remains unchanged.

### Simulate Different Producers

You can also tag messages as if they came from different producer instances:

```powershell
$body = @{
  topic = "retailflow.direct.order_signals.partitioned"
  event_type = "order.signal.created"
  producer_id = "producer-a"
  partition_key_strategy = "order_id"
  payload = @{
    order_id = 201
    store_code = "BLR-001"
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/events/direct-publish/" `
  -ContentType "application/json" `
  -Body $body
```

Then repeat with:

```text
producer-b
producer-c
```

These producers can all publish to the same topic. Kafka will still assign partitions by key, not by the producer name.

## 11A. Multi-Partition and Multi-Consumer-Group Demo

This project now includes a helper script to run consumers with explicit:

- group id
- consumer name
- topic list

Script:

```powershell
.\scripts\kafka\run-consumer-group.ps1 <group-id> <consumer-name> <topics>
```

### Same Group Demo

Open terminal 1:

```powershell
.\scripts\kafka\run-consumer-group.ps1 retailflow-demo-group-a consumer-a1 retailflow.direct.order_signals.partitioned
```

Open terminal 2:

```powershell
.\scripts\kafka\run-consumer-group.ps1 retailflow-demo-group-a consumer-a2 retailflow.direct.order_signals.partitioned
```

Meaning:

- both consumers belong to the same group
- Kafka divides partitions among group members
- one message is processed by one member of that group, not both

### Different Group Demo

Open terminal 3:

```powershell
.\scripts\kafka\run-consumer-group.ps1 retailflow-demo-group-b consumer-b1 retailflow.direct.order_signals.partitioned
```

Meaning:

- `retailflow-demo-group-b` is a different group from `retailflow-demo-group-a`
- this new group gets its own independent view of the same topic
- both groups can consume the same topic without interfering with each other

What to observe in the logs:

- `consumer_group`
- `consumer_name`
- `partition`
- `offset`
- `key`

Expected learning:

- same key usually lands on the same partition
- consumers in the same group share partitions
- different groups each receive the topic independently

## 11B. AWS Messaging Sample Endpoints

The project now includes sample AWS integration endpoints for:

- SQS publish
- SNS publish
- AWS config probe

These are learning-focused integrations so you can understand code-to-AWS wiring before full Terraform automation.

### Check AWS Config Wiring

```powershell
Invoke-RestMethod "http://localhost:8000/api/events/aws-config-probe/"
```

Expected response includes:

- `aws_region`
- `sqs_configured`
- `sns_configured`

### Publish Sample Message to SQS

Set `AWS_SQS_QUEUE_URL` in `.env` first.

Then run:

```powershell
$body = @{
  event_type = "order.signal.created"
  payload = @{
    order_id = 301
    store_code = "BLR-001"
    channel = "sqs-demo"
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/events/aws-sqs-publish/" `
  -ContentType "application/json" `
  -Body $body
```

Optional FIFO queue note:

- if you use an SQS FIFO queue, pass `message_group_id`

### Publish Sample Message to SNS

Set `AWS_SNS_TOPIC_ARN` in `.env` first.

Then run:

```powershell
$body = @{
  event_type = "order.signal.created"
  payload = @{
    order_id = 302
    store_code = "BLR-001"
    channel = "sns-demo"
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/events/aws-sns-publish/" `
  -ContentType "application/json" `
  -Body $body
```

### Lambda Sample Included in Repo

A sample Lambda handler now exists at:

```text
lambda/order_signal_notifier/handler.py
```

Current sample flow:

```text
SQS event -> Lambda handler -> CloudWatch Logs
```

The Phase 1 Lambda behavior is intentionally simple:

- Lambda is triggered by SQS
- Lambda logs the incoming message to CloudWatch
- Lambda does not publish to SNS yet

If you created the Lambda in AWS using the default file name `lambda_function.py`, paste the contents of `lambda/order_signal_notifier/handler.py` into that file and keep the default handler name:

```text
lambda_function.lambda_handler
```

### Phase 1 Verification Flow

After the SQS trigger is attached to Lambda and `AWS_SQS_QUEUE_URL` is configured locally:

1. Start your local Django API
2. Call `GET /api/events/aws-config-probe/`
3. Call `POST /api/events/aws-sqs-publish/`
4. Open the Lambda function in AWS
5. Go to `Monitor`
6. Open CloudWatch logs
7. Verify the message body was logged by Lambda

## 12. Verify CDC Pipeline

Create an order:

```powershell
$body = @{
  store = 1
  lines = @(
    @{
      sku = 1
      requested_quantity = 2
    }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/orders/" `
  -ContentType "application/json" `
  -Body $body
```

Expected:

- Django returns an order with status `created`.
- Celery later updates status to `processing`.
- Debezium emits table changes to `retailflow.public.orders_order`.
- Kafka consumer prints the CDC event.

Read order:

```powershell
Invoke-RestMethod "http://localhost:8000/api/orders/1/"
```

## 13. Useful Docker Commands

Container status:

```powershell
docker ps
```

Compose status:

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml ps
```

Logs:

```powershell
docker logs retailflow-postgres
docker logs retailflow-redis
docker logs retailflow-kafka
docker logs retailflow-kafka-connect
docker logs retailflow-api
docker logs retailflow-celery-worker
docker logs retailflow-kafka-consumer
```

Stop containers without deleting data:

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml down
```

Stop containers and delete volumes:

```powershell
docker compose -f infra\docker-compose\docker-compose.local.yml down -v
```

Use `down -v` only when you want a fresh database and fresh Kafka state.

## 14. Common Issues

### Docker Pipe Error

If Docker says it cannot access `dockerDesktopLinuxEngine`, open Docker Desktop and wait until it is fully running.

### PowerShell Curl Issue

PowerShell aliases `curl` to `Invoke-WebRequest`. Prefer `Invoke-RestMethod` for API calls.

### Topic Already Has One Partition

If `retailflow.direct.order_signals` was auto-created with one partition, use:

```text
retailflow.direct.order_signals.partitioned
```

Do not rely on `--if-not-exists` to change partition count. It will leave an existing topic unchanged.

## 15. Current Next Engineering Step

Next infra-first implementation step:

1. Verify the full containerized app stack locally.
2. Let GitHub Actions run lint, Django checks, migration checks, tests, and Docker image builds.
3. Then move into AWS tooling and service integrations.

## 16. CI Verification

GitHub Actions now checks:

- `ruff check backend workers`
- `python backend/manage.py check`
- `python backend/manage.py makemigrations --check --dry-run`
- `python backend/manage.py migrate`
- `pytest`
- `docker build -t retailflow-api:ci backend`
- `docker build -t retailflow-kafka-consumer:ci workers/kafka_consumer`

## 17. EC2 CD Verification

The `Deploy Dev` GitHub Actions workflow now verifies application health from inside the EC2 instance over SSH instead of curling the public IP from the GitHub runner.

Why this is better for the current setup:

- It avoids false negatives caused by security-group differences between your laptop and GitHub-hosted runners.
- It checks whether the app is actually healthy on the VM after deployment.
- It keeps the deployment verification closer to the service itself.

Current workflow behavior:

1. SSH into EC2
2. Pull the selected branch
3. Run `bash scripts/aws/deploy-ec2.sh`
4. Retry `curl http://localhost:8000/health/` on the EC2 host up to 12 times with a 5 second delay

If the workflow fails in the health step now, it usually means the API container itself did not come up cleanly, not just that the public port was unreachable from GitHub Actions.
