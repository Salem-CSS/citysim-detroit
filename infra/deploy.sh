#!/usr/bin/env bash
# Deploy the CitySim backend for one person / stage.
#   ./infra/deploy.sh salem            # your own test stack: citysim-salem
#   ./infra/deploy.sh partner          # partner's test stack
#   ./infra/deploy.sh main             # shared stack the website uses (deploy from main only)
# Needs: AWS CLI v2 + SAM CLI, credentials for the CitySim account (AWS_PROFILE=citysim), region us-east-1.
set -euo pipefail
STAGE="${1:?usage: deploy.sh <salem|partner|main> [extra sam args]}"; shift || true
cd "$(dirname "$0")/.."
REGION="${AWS_REGION:-us-east-1}"

# Package only the backend code (keeps the web tiles out of the Lambda zip).
rm -rf infra/.build && mkdir -p infra/.build/src
cp -r agent contracts engine residents infra/.build/src/
mkdir -p infra/.build/src/infra && cp infra/__init__.py infra/runs.py infra/.build/src/infra/
find infra/.build/src -name tests -type d -prune -exec rm -rf {} + -o -name __pycache__ -type d -prune -exec rm -rf {} +

sam deploy \
  --template-file infra/template.yaml \
  --stack-name "citysim-$STAGE" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-fail-on-empty-changeset \
  --parameter-overrides "Stage=$STAGE" "$@"

aws cloudformation describe-stacks --stack-name "citysim-$STAGE" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text
