#!/usr/bin/env bash
set -e

COMPANY_ID=${1:?"Usage: ./run_seed.sh <company_id>"}

echo "Copying seed script into api container..."
docker compose cp seed_incidents.py api:/tmp/seed_incidents.py

echo "Running seed for company_id=$COMPANY_ID..."
docker compose exec api bash -c "python /tmp/seed_incidents.py $COMPANY_ID"
