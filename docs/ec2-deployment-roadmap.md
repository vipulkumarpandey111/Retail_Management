# EC2 Deployment Roadmap

This document explains the EC2 deployment path that is now implemented in the project.

It focuses on three things:

1. why we chose EC2 first
2. what was configured on the VM
3. how GitHub Actions deploys to it now

## 1. Why EC2 Was the Right First Cloud Step

We intentionally chose EC2 before RDS, Terraform-heavy AWS provisioning, or Kubernetes on AWS.

Why:

- simplest cloud compute mental model
- Free Tier-friendly compared to bigger managed platforms
- enough to learn SSH, Linux, Docker, Compose, security groups, and deployment
- avoids jumping too early into EKS or MSK complexity

This gave us a fast path from "local Dockerized app" to "real cloud deployment."

## 2. What the Current EC2 Runtime Includes

The EC2 deployment is intentionally a reduced stack:

- Django API
- Celery worker
- PostgreSQL
- Redis

It does not currently include:

- Kafka
- Zookeeper
- Kafka Connect
- Debezium
- Kafka consumer

Why this split exists:

- local is the full infra lab
- EC2 is the lighter deployment lab
- Kafka-heavy services would make a small VM less comfortable

## 3. Files That Control EC2 Deployment

Main files:

- [infra/docker-compose/docker-compose.ec2.yml](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\infra\docker-compose\docker-compose.ec2.yml)
- [infra/ec2/.env.ec2.example](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\infra\ec2\.env.ec2.example)
- [scripts/aws/ec2-bootstrap.sh](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\scripts\aws\ec2-bootstrap.sh)
- [scripts/aws/deploy-ec2.sh](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\scripts\aws\deploy-ec2.sh)
- [.github/workflows/deploy-dev.yml](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\.github\workflows\deploy-dev.yml)

## 4. What We Configured on EC2

### A. Instance launch

We launched:

- Ubuntu
- `ap-south-1`
- Free Tier-conscious instance type

### B. Security groups

At minimum we worked with:

- port `22` for SSH
- port `8000` for the API

Important note:

- in the current learning-stage setup, these may be open to `0.0.0.0/0`
- that is useful for getting GitHub Actions and public testing working
- it is not the final hardened shape

### C. Docker installation

We used:

- [scripts/aws/ec2-bootstrap.sh](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\scripts\aws\ec2-bootstrap.sh)

What it does:

1. installs system prerequisites
2. adds Docker's apt repository
3. installs Docker Engine and Compose plugin
4. adds the current user to the `docker` group
5. enables and starts Docker

Why each part matters:

- Docker Engine runs containers
- Compose plugin runs multi-service stacks
- docker group access avoids needing `sudo` for every Docker command

### D. Repo clone and env file

On EC2 we:

1. cloned the repo
2. created `infra/ec2/.env.ec2`
3. filled in deployment-specific values

Typical values include:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_PASSWORD`

Why:

- local config should not be reused blindly on EC2
- container networking on EC2 is different from local host networking

## 5. How the EC2 Compose File Works

The EC2 stack is defined in:

- [infra/docker-compose/docker-compose.ec2.yml](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\infra\docker-compose\docker-compose.ec2.yml)

Important behavior:

- API builds from the backend Dockerfile
- API runs migrations before starting Gunicorn
- API binds to `0.0.0.0:8000`
- API exposes `8000:8000`
- Celery worker uses the same backend image with a different command
- Postgres and Redis use named Docker volumes for persistence

Why this is useful:

- app startup is mostly self-contained
- worker and API share the same code image
- data survives container restarts because of volumes

## 6. How Manual Deployment Works

Manual deployment is done through:

- [scripts/aws/deploy-ec2.sh](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\scripts\aws\deploy-ec2.sh)

What it does:

1. move into the project directory
2. verify `infra/ec2/.env.ec2` exists
3. run `docker compose up -d --build`
4. print compose status

This keeps the deployment script intentionally small and easy to understand.

## 7. How CD Works Now

The GitHub Actions deployment workflow is:

- [.github/workflows/deploy-dev.yml](C:\Users\vipul\OneDrive\Desktop\SelfDev\DevHandsOn\.github\workflows\deploy-dev.yml)

Current step-by-step flow:

1. manual trigger from GitHub Actions
2. checkout repo
3. start SSH agent with private key from GitHub secret
4. add EC2 host to `known_hosts`
5. SSH into EC2
6. `git fetch origin`
7. `git checkout <branch>`
8. `git pull origin <branch>`
9. run `bash scripts/aws/deploy-ec2.sh`
10. run health check from inside EC2 using `curl http://localhost:8000/health/`

That last step is important.

Earlier we tried checking the public EC2 IP from the GitHub runner. That led to false failures because public network reachability and runner source IPs can be tricky. So we changed the health check to run on the VM itself.

That is a better fit for the current project stage.

## 8. GitHub Secrets Used for CD

Current deployment secrets:

- `EC2_HOST`
- `EC2_USER`
- `EC2_APP_DIR`
- `EC2_SSH_PRIVATE_KEY`
- `DEPLOY_HEALTHCHECK_HOST`

What they do:

- `EC2_HOST`: tells the workflow where to SSH
- `EC2_USER`: Linux username on the EC2 machine
- `EC2_APP_DIR`: repo path on the VM
- `EC2_SSH_PRIVATE_KEY`: private key used for SSH authentication
- `DEPLOY_HEALTHCHECK_HOST`: kept from the earlier external health-check approach

Why use GitHub secrets:

- values do not live in committed YAML
- they are masked in logs
- changing them does not require code changes

## 9. Current Strengths of This Setup

The current EC2 deployment path is strong for learning because it teaches:

- cloud VM basics
- Linux operations
- Docker Compose deployment
- environment configuration
- secret handling
- port and networking thinking
- CI/CD integration
- troubleshooting using logs and health checks

## 10. Current Weaknesses of This Setup

This is not yet the final shape, and that is okay.

Current limitations:

- database is still on the same VM as the app
- Redis is still on the same VM as the app
- security-group exposure can still be too broad
- Kafka is not yet part of cloud deployment
- no managed AWS services are integrated yet
- no Terraform-managed cloud resources yet

These are exactly the kinds of improvements that should come next.

## 11. Best Next Steps After EC2 + CD

Recommended next order:

1. move PostgreSQL from EC2 container to RDS
2. reduce exposure in security groups
3. improve deployment environment separation
4. add AWS services like SQS, SNS, S3, or Lambda
5. introduce Terraform where it adds clarity and repeatability

## 12. Short Version

If you want the shortest summary:

we used EC2 as the first cloud deployment target because it teaches the most important backend deployment basics with the least moving parts, and we now have a working GitHub Actions pipeline that can deploy this reduced Docker Compose stack to that VM.
