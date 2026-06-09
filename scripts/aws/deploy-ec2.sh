#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$HOME/Retail_Management}"

cd "$PROJECT_DIR"

if [ ! -f "infra/ec2/.env.ec2" ]; then
  echo "Missing infra/ec2/.env.ec2"
  exit 1
fi

docker compose -f infra/docker-compose/docker-compose.ec2.yml up -d --build
docker compose -f infra/docker-compose/docker-compose.ec2.yml ps

