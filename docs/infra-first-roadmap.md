# Infra-First Roadmap

This roadmap assumes the current V1 foundation is already in place:

- local full-stack infra works
- Dockerized runtime works
- CI works
- CD works
- EC2 deployment works

So from here onward, the work is less about proving that infra exists and more about improving separation, security, and cloud integrations.

## 1. Current V1 Status

Already implemented:

- PostgreSQL in Docker Compose
- Redis for cache and Celery
- Celery async task execution
- Kafka local stack
- Debezium CDC
- direct Kafka publishing
- Kafka consumer classification
- Dockerized services
- GitHub Actions CI
- GitHub Actions CD
- EC2 deployment using reduced Docker Compose stack

This means the project already covers the first meaningful backend-infra lifecycle.

## 2. What the Next Steps Should Optimize

The main categories now are:

### A. Better separation

Example:

- move database out of EC2 into RDS

### B. Better security

Examples:

- reduce public exposure on ports
- avoid broad `0.0.0.0/0` rules where possible

### C. Better cloud integration

Examples:

- SQS
- SNS
- S3
- Lambda

### D. Better infrastructure-as-code

Examples:

- Terraform for cloud resources

## 3. Recommended Next-Step Order

### Step 1: Move PostgreSQL from EC2 container to RDS

Why first:

- biggest architecture improvement
- very common real-world separation
- lets the app VM become more stateless
- teaches managed database thinking

What changes:

- EC2 app containers stop talking to local `postgres`
- app talks to RDS endpoint instead
- DB security is handled through VPC and security groups instead of Docker-internal networking

### Step 2: Tighten EC2 networking and deployment exposure

Why second:

- once deployment is stable, hardening becomes easier
- current learning-stage rules may be broader than desired

Possible improvements:

- narrow SSH access
- narrow port `8000` access depending on the verification path
- keep health checks internal where possible

### Step 3: Improve CD behavior

Why third:

- CD already works, so now it can be refined

Examples:

- require CI success before deploy
- auto-deploy selected branches only
- define clearer `dev` vs future `prod` flow

### Step 4: Add one AWS service integration at a time

Best learning order:

1. SQS
2. SNS
3. S3
4. Lambda

Why this order:

- SQS is simple and useful
- SNS introduces pub-sub
- S3 introduces storage
- Lambda introduces event-driven serverless compute

### Step 5: Introduce Terraform

Why after the basics are clear:

- Terraform is easier to understand once you already know the AWS resources manually
- otherwise you are learning AWS and Terraform at the same time

Good candidates for first Terraform resources:

- RDS
- SQS
- SNS
- S3
- IAM policies related to those services

## 4. A Practical Learning Sequence

If the goal is to keep learning smooth and not overwhelming, this is the best sequence:

1. understand the current local + CI/CD + EC2 setup deeply
2. move Postgres to RDS
3. tighten security groups
4. add SQS from application or worker code
5. add SNS
6. add S3
7. add Lambda
8. automate those AWS resources with Terraform

## 5. What We Are Not Prioritizing Yet

These are intentionally not the immediate next steps:

- Kubernetes on AWS
- MSK
- EKS
- Aurora
- large-scale observability stack

Why:

- they add complexity fast
- they are less Free Tier-friendly
- they are not necessary yet to understand the core backend infra path

## 6. Short Version

The project has already crossed the first major infra milestone.

So the next roadmap is:

1. separate DB from app VM
2. tighten security
3. improve CD discipline
4. add AWS services one by one
5. automate cloud resources with Terraform
