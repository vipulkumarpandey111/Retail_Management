# Infra-First Implementation Roadmap

This roadmap prioritizes infrastructure learning over deep retail business logic. Business behavior should remain realistic enough to generate useful events, but the main goal is understanding how tools integrate.

## Current Local Capabilities

- PostgreSQL runs in Docker Compose on host port `5433`.
- Redis runs in Docker Compose and is used by both Celery and Django cache.
- Celery runs locally and uses Redis as broker/result backend.
- Kafka, Zookeeper, Kafka Connect, and Debezium run in Docker Compose.
- Debezium captures PostgreSQL changes into Kafka CDC topics.
- Django can publish direct application events to Kafka.
- Kafka consumer reads both direct Kafka events and Debezium CDC events.

## Next Implementation Flow

### 1. Kafka Partitioning Demo

Goal: understand how Kafka assigns messages to partitions.

Implementation:

- Create `retailflow.direct.order_signals.partitioned` with multiple partitions.
- Publish messages with different key strategies:
  - `event_type`
  - `order_id`
  - `custom`
- Observe partition/offset in producer response and consumer logs.

Why this matters:

- Kafka preserves ordering only within a partition.
- Same key usually maps to the same partition.
- Partitioning strategy affects scalability and event ordering.

### 2. Kafka Consumer Classification

Goal: make event origins obvious.

Implementation:

- If topic starts with `retailflow.public.`, classify as Debezium CDC.
- If topic starts with `retailflow.direct.`, classify as direct application event.
- Print normalized event summaries.
- Later store selected consumed events in `EventLog`.

### 3. Dockerize Application Services

Goal: move from mixed local processes to containerized services.

Implementation:

- Add Dockerfile for Django API.
- Run Celery worker from same image with a different command.
- Add Dockerfile for Kafka consumer or reuse a shared Python image.
- Extend Docker Compose to include API, worker, and consumer.

Why before EC2:

- EC2 Docker Compose deployment should run the same service definitions we already tested locally.

### 4. GitHub Actions CI

Goal: make every push verify the app.

Implementation:

- Run lint.
- Run Django checks.
- Run migration checks.
- Run tests with Postgres and Redis service containers.
- Later build Docker images.

Why before AWS:

- It creates a quality gate before deployment.

### 5. AWS Tooling Setup

Goal: prepare local and CI environments for AWS safely.

Implementation:

- Install AWS CLI v2.
- Install Terraform.
- Confirm account identity with `aws sts get-caller-identity`.
- Use `ap-south-1`.
- Add AWS budget alert manually in console before creating resources.

Free-tier posture:

- Avoid EKS, MSK, NAT Gateway, Aurora by default.
- Prefer local Kafka over MSK.
- Prefer EC2 Docker Compose before Kubernetes-on-EC2.
- Use tiny S3/SQS/SNS/Lambda examples.

### 6. AWS Service Integrations

Goal: connect the local event system to low-cost AWS services.

Implementation order:

1. SQS queue for selected events.
2. SNS topic for notifications.
3. S3 bucket for tiny archived event payloads.
4. Lambda function that reads from SQS and writes to S3.

Learning flow:

```text
Kafka consumer -> SQS -> Lambda -> S3
                         -> SNS
```

### 7. EC2 Docker Compose Deployment

Goal: run the service on a Free Tier-compatible EC2 path.

Implementation:

- Build Docker images.
- Create EC2 instance.
- Install Docker and Docker Compose plugin.
- Copy deployment Compose file and env file.
- Start API, worker, consumer, Redis, and optionally Postgres.

Important decision:

- For first EC2 deployment, keep Kafka local-only or run a reduced event stack on EC2 depending on instance capacity.
- Kafka can be memory-heavy for tiny EC2 instances, so we should introduce it carefully.

### 8. Traffic Simulation

Goal: simulate realistic traffic without high cost.

Implementation:

- Add a lightweight script that sends order events and direct Kafka events.
- Run locally first.
- Run against EC2 API later.
- Observe API logs, Celery logs, Kafka consumer logs, and resource usage.

## Recommended Immediate Sequence

1. Run the Kafka partitioning demo.
2. Improve Kafka consumer classification.
3. Dockerize API, Celery, and consumer.
4. Expand Docker Compose to run the full local app stack.
5. Add CI checks in GitHub Actions.
6. Add AWS SQS/SNS/S3/Lambda Terraform and code.
7. Deploy a Docker Compose version to EC2.
