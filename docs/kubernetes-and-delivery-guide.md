# Kubernetes and Delivery Guide

This document is the growing learning guide for the "how does backend code actually become a running system?" part of the project.

It starts top down and stays practical. As we add more infra, we can keep extending this same file instead of scattering the mental model across many places.

## 1. The Full Path From Code To Running App

This is the main picture to keep in your head:

```text
Code
-> local app runtime
-> local infrastructure
-> container image
-> CI verification
-> CD deployment
-> cloud runtime
-> monitoring and debugging
-> future scaling/orchestration
```

For this project today, that becomes:

```text
Django code
-> runs locally with Postgres, Redis, Kafka, Debezium
-> packaged into Docker images
-> validated by GitHub Actions CI
-> deployed to EC2 by GitHub Actions CD
-> runs on EC2 with Docker Compose
-> verified through health checks, logs, and CloudWatch
-> ready to evolve toward Kubernetes
```

That is the full delivery lifecycle we have already built in V1 form.

## 2. What We Have Already Covered Well

This project already gives you hands-on exposure to:

- local infra setup
- transactional database wiring
- cache wiring
- async worker execution
- event streaming
- CDC flow
- Docker images and Compose runtime
- CI quality checks
- CD deployment automation
- EC2 operations
- AWS SDK-based messaging integration
- secrets and env-based configuration
- logs-first debugging

That is already a strong backend-infra foundation for an application engineer.

## 3. The Runtime Layers In This Project

You can understand the system in six layers.

### Layer 1: Application Code

The Django app contains the API, serializers, domain models, and service behavior.

Main places:

- [backend/retailflow/settings.py](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\backend\retailflow\settings.py)
- [backend/apps/orders](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\backend\apps\orders)
- [backend/apps/events](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\backend\apps\events)

### Layer 2: State and Storage

PostgreSQL stores the source of truth.

Right now:

- local full stack uses containerized Postgres
- EC2 reduced stack also uses containerized Postgres
- future improvement can move DB to RDS

### Layer 3: Cache and Async Work

Redis and Celery provide:

- cache storage
- task broker
- background processing

That is the first step beyond a purely synchronous backend.

### Layer 4: Eventing

Kafka and Debezium provide:

- direct application event publishing
- CDC-based event publishing from DB changes
- partition, consumer-group, and offset learning

### Layer 5: Packaging and Runtime

Docker and Docker Compose provide:

- reproducible local runtime
- reproducible EC2 runtime
- a bridge from app code to deployable services

### Layer 6: Delivery and Operations

GitHub Actions, EC2, and AWS integrations provide:

- automated validation
- automated deployment
- cloud execution
- logs and operational feedback

## 4. Delivery Path In This Repo

Here is the delivery path in very plain language.

### Step A: Write or change code

You change Django app code, worker code, config, or scripts.

### Step B: Run it locally

We verify locally using:

- `python backend/manage.py runserver`
- `docker compose`
- Redis, Postgres, Kafka, Debezium
- PowerShell API calls

This is where most fast feedback happens.

### Step C: Package it into images

The app and Kafka consumer can be built as Docker images.

Main files:

- [backend/Dockerfile](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\backend\Dockerfile)
- [workers/kafka_consumer/Dockerfile](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\workers\kafka_consumer\Dockerfile)

### Step D: Let CI verify the repo

CI checks:

- lint
- Django checks
- migration consistency
- tests
- Docker builds

Main file:

- [.github/workflows/ci.yml](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\.github\workflows\ci.yml)

### Step E: Trigger deployment

CD uses GitHub Actions to:

- SSH into EC2
- update repo state
- run deployment script
- verify service health

Main file:

- [.github/workflows/deploy-dev.yml](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\.github\workflows\deploy-dev.yml)

### Step F: App runs on the cloud VM

EC2 currently runs the reduced Compose stack:

- API
- Celery worker
- Postgres
- Redis

That keeps the VM light and still teaches real deployment.

## 5. Docker Image To Deployment Pipeline

This is one of the most important infra ideas to know.

The practical pipeline is:

```text
source code
-> dependency install
-> build Docker image
-> run checks/tests
-> deploy image/runtime to target environment
-> verify health
-> inspect logs if anything fails
```

In this repo, the deployment target is not Kubernetes yet. It is EC2 plus Docker Compose.

So the current mental model is:

```text
GitHub Actions CD
-> SSH to EC2
-> pull repo
-> docker compose up
-> health check
```

Later, if we move to Kubernetes, only the deployment target changes. The general software-delivery idea stays the same.

## 6. Kubernetes Concepts You Should Know Next

You asked specifically about the near-term concepts worth knowing. Here is the practical version, mapped to what you already know.

### Pods

A Pod is the smallest runnable unit in Kubernetes.

Practical mental model:

- today: Docker container started on a machine
- in Kubernetes: container is usually run inside a Pod managed by the cluster

Important point:

- Pods are replaceable
- they are not meant to be manually cared for one by one

### Deployments

A Deployment manages Pods for stateless applications.

It defines:

- which image to run
- how many replicas to keep alive
- how updates roll out

Mapping to your current setup:

- today: Compose says run one API container
- later: Deployment says keep N API Pods running

### Services

A Service gives stable networking to a changing set of Pods.

Why it exists:

- Pod IPs change
- the rest of the system still needs one stable name/address

Mapping:

- today: app reaches another service by Compose service name or host port
- later: app reaches another workload by Kubernetes Service name

### Ingress

Ingress is the HTTP entry layer for external traffic.

It usually handles:

- path-based routing
- domain-based routing
- TLS termination

Mapping:

- today: EC2 public IP + open port `8000`
- later: Ingress controller routes traffic to the Django Service

### ConfigMaps

ConfigMaps store non-secret configuration.

Examples:

- topic name
- queue URL
- app mode
- feature flags

### Secrets

Secrets store sensitive values.

Examples:

- DB passwords
- AWS credentials
- API keys

Mapping:

- today: `.env`, GitHub Secrets, EC2 env file
- later: Kubernetes Secrets injected into Pods

## 7. How Rolling Deployment Works

Rolling deployment means the new version comes up gradually instead of replacing everything at once.

Typical flow:

1. start new Pods
2. wait until they are healthy
3. shift traffic
4. remove old Pods

Why this matters:

- less downtime
- safer releases
- easier rollback behavior

What makes rolling deploys trustworthy:

- readiness checks
- liveness checks
- graceful startup
- graceful shutdown

This is why health endpoints are not just cosmetic. They are part of deployment correctness.

## 8. How Scaling Works

In practical terms, scaling usually means increasing replica count.

Examples:

- API from 1 instance to 3
- worker from 1 instance to 4

Kinds of scaling:

- vertical scaling: give one instance more CPU/RAM
- horizontal scaling: run more instances

Kubernetes is especially strong at horizontal scaling for stateless services.

Important nuance:

- Django API is easier to scale
- Celery workers are usually fairly easy to scale
- Postgres, Kafka, and Redis need more care because they are stateful

That is why managed database services are often separated before app workloads are fully orchestrated.

## 9. Logs And Debugging With kubectl

When you eventually move to Kubernetes, these are the commands that matter first:

```bash
kubectl get pods
kubectl get deployments
kubectl get services
kubectl logs <pod-name>
kubectl describe pod <pod-name>
kubectl exec -it <pod-name> -- sh
kubectl rollout status deployment/<name>
kubectl rollout history deployment/<name>
```

What they correspond to in your current experience:

- `docker ps` -> what is running
- `docker logs` -> app output
- SSH + inspect container -> runtime debugging
- GitHub Actions logs -> deployment feedback

So Kubernetes debugging is not a new kind of thinking. It is mostly the same operational thinking through different commands.

## 10. What We Have Not Yet Covered Deeply

These are the main knowledge areas still worth learning after this checkpoint:

- readiness vs liveness probes
- resource requests and limits
- persistent volumes
- internal cluster DNS
- image registry flow
- ingress controller behavior
- namespaces and environment separation
- autoscaling basics

These are the natural next topics once you are comfortable with the current project lifecycle.

## 11. Where Terraform Fits

Terraform fits in the provisioning layer, not the runtime-call layer.

Use Terraform when you want to declare:

- EC2
- security groups
- SQS
- SNS
- Lambda
- RDS
- IAM roles/policies

Use `boto3` when the running application wants to use those resources.

Simple rule:

- app uses cloud services at runtime -> `boto3`
- team creates/manages cloud resources declaratively -> Terraform

That distinction matters a lot in real systems.

## 12. Recommended Learning Order From Here

Given what you have already built, this is the next practical order I'd recommend.

1. Strengthen the current AWS integrations a bit more
2. Understand one small Terraform-managed AWS resource flow
3. Learn Kubernetes by mapping this same project into:
   - one Deployment
   - one Service
   - one ConfigMap
   - one Secret
4. Practice scaling and rollout commands locally on Docker Desktop Kubernetes
5. Only then go deeper into multi-service Kubernetes patterns

That keeps the learning curve sharp but not chaotic.

## 13. Repo Files To Read Alongside This Guide

Read these in this order when you want the concrete implementation side.

1. [README.md](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\README.md)
2. [running.md](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\running.md)
3. [docs/project-explainer.md](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\docs\project-explainer.md)
4. [infra/docker-compose/docker-compose.local.yml](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\infra\docker-compose\docker-compose.local.yml)
5. [infra/docker-compose/docker-compose.ec2.yml](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\infra\docker-compose\docker-compose.ec2.yml)
6. [.github/workflows/ci.yml](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\.github\workflows\ci.yml)
7. [.github/workflows/deploy-dev.yml](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\.github\workflows\deploy-dev.yml)

## 14. Final Mental Model

The cleanest short summary is:

This project already teaches the real path from backend code to a deployed service, and Kubernetes is the next orchestration layer on top of foundations you now already understand.
