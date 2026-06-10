# EC2 Deployment Roadmap

This document defines the EC2-first deployment path for RetailFlow Lab. The goal is to keep the first cloud deployment Free Tier-conscious and operationally simple, then add more AWS services later.

## Why EC2 First

For this project, EC2 is enough to understand backend infrastructure concepts:

- virtual machine setup
- SSH access
- Docker and Docker Compose
- process isolation with containers
- ports and security groups
- environment variable management
- deployment updates
- log inspection
- basic monitoring

We do not need SQS, SNS, S3, Lambda, or Kubernetes on day one to start learning deployment and backend operations.

## Free Tier-Safe Approach

Recommended first EC2 deployment shape:

- Django API
- Celery worker
- Redis
- PostgreSQL

Kafka, Zookeeper, Kafka Connect, and Debezium stay local for now.

Reason:

- Kafka is comparatively memory-heavy for a tiny EC2 instance.
- A reduced stack is much safer for Free Tier usage.
- We can still learn deployment, VM operations, Docker Compose, and CD without adding avoidable cost or instability.

## Monitoring Recommendation

Use the simplest low-overhead path first:

- EC2 basic monitoring in CloudWatch
- AWS Budgets cost alert
- Docker logs on the instance

According to AWS docs:

- EC2 basic monitoring is enabled by default and publishes standard metrics every 5 minutes.
- EC2 detailed monitoring publishes 1-minute metrics and incurs extra CloudWatch charges.
- AWS Budgets can be used to track cost and send alerts.

So for this stage:

- keep basic monitoring
- do not enable detailed monitoring yet
- create a small monthly budget alert

## User Steps

### 1. Confirm Free Tier Eligibility

You need to confirm:

- whether your AWS account is still in its Free Tier eligibility window
- which EC2 instance types are Free Tier-eligible for your account

Useful AWS docs:

- [Track your Free Tier usage for Amazon EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html)
- [Confirming eligibility to use AWS Free Tier](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-eligibility.html)

### 2. Create Cost Guardrails

Before launching anything:

- create an AWS Budget with a very small threshold
- use email alerts

Useful AWS docs:

- [Creating a budget](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-create.html)
- [Control Your AWS Costs](https://docs.aws.amazon.com/hands-on/latest/control-your-costs-free-tier-budgets/control-your-costs-free-tier-budgets.html)

### 3. Launch EC2 Instance

Recommended starting point:

- Ubuntu LTS
- Free Tier-eligible instance family for your account
- `ap-south-1`
- security group with:
  - `22` for SSH from your IP only
  - `8000` from your IP for API testing

Do not open:

- `5432`
- `6379`

PostgreSQL and Redis should remain internal to Docker.

### 4. SSH Into EC2 And Install Docker

Run:

```bash
bash scripts/aws/ec2-bootstrap.sh
```

Reconnect SSH after the script finishes.

### 5. Clone Repo On EC2

Example:

```bash
git clone <your-repo-url> ~/Retail_Management
cd ~/Retail_Management
```

### 6. Create EC2 Environment File

Copy:

```bash
cp infra/ec2/.env.ec2.example infra/ec2/.env.ec2
```

Edit:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_PASSWORD`

Important:

- the same `POSTGRES_PASSWORD` value is used by both the Django containers and the PostgreSQL container
- if you change it after PostgreSQL has already initialized its data directory, you should recreate the PostgreSQL volume for a clean first deployment

### 7. Start Reduced Stack

Run:

```bash
bash scripts/aws/deploy-ec2.sh
```

This uses:

```text
infra/docker-compose/docker-compose.ec2.yml
```

For a first deployment, if the database password was changed after the first container startup, reset the stack with:

```bash
docker compose -f infra/docker-compose/docker-compose.ec2.yml down -v
```

Then start it again so PostgreSQL initializes with the same password used by the app containers.

### 8. Verify Deployment

From your laptop:

```powershell
Invoke-RestMethod "http://<ec2-public-ip>:8000/health/"
```

On EC2:

```bash
docker compose -f infra/docker-compose/docker-compose.ec2.yml ps
docker logs retailflow-api
docker logs retailflow-celery-worker
```

### 9. Add CD After EC2 Works

Only after the manual EC2 deployment is healthy should we automate it.

The current CD workflow now does this:

- trigger manually first
- accept a branch input
- SSH into EC2
- `git fetch`
- `git checkout <branch>`
- `git pull`
- run `bash scripts/aws/deploy-ec2.sh`
- run an external `/health/` check from GitHub Actions

### 10. GitHub Secrets Required For CD

Create these repository secrets in GitHub:

- `EC2_HOST`
  - example: `52.66.235.103`
- `EC2_USER`
  - example: `ubuntu`
- `EC2_APP_DIR`
  - example: `/home/ubuntu/Retail_Management`
- `EC2_SSH_PRIVATE_KEY`
  - the full contents of your `.pem` private key
- `DEPLOY_HEALTHCHECK_HOST`
  - example: `52.66.235.103`

### 11. How To Run CD

In GitHub:

1. Open the repo
2. Go to `Actions`
3. Open `Deploy Dev`
4. Click `Run workflow`
5. Keep `main` as the branch for now
6. Run the workflow

If successful, the workflow:

- connects to EC2
- updates the checked-out repo
- rebuilds and restarts the reduced stack
- confirms `/health/` returns success

## Project Steps I Am Taking Next

The repo is now prepared with:

- `infra/docker-compose/docker-compose.ec2.yml`
- `infra/ec2/.env.ec2.example`
- `scripts/aws/ec2-bootstrap.sh`
- `scripts/aws/deploy-ec2.sh`
- `.github/workflows/deploy-dev.yml`

The next code step after this should be:

- move PostgreSQL from EC2 container to RDS after the CD workflow is verified
