#!/usr/bin/env bash
# Upload ui/dist to the frontend S3 bucket and invalidate CloudFront.
# Run from repository root after: make ui-build && cdk deploy TechBlogFrontendStack

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d ui/dist ]]; then
  echo "ui/dist missing — run: make ui-build" >&2
  exit 1
fi

BUCKET="$(aws cloudformation describe-stacks \
  --stack-name TechBlogFrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='WebsiteBucketName'].OutputValue" \
  --output text)"
DIST_ID="$(aws cloudformation describe-stacks \
  --stack-name TechBlogFrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='DistributionId'].OutputValue" \
  --output text)"
API_URL="$(aws cloudformation describe-stacks \
  --stack-name TechBlogApiStack \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text)"
API_URL="${API_URL%/}"

echo "Syncing ui/dist -> s3://${BUCKET}"
aws s3 sync ui/dist "s3://${BUCKET}" --delete

echo "Writing config.json (apiUrl=${API_URL})"
printf '{"apiUrl":"%s"}' "$API_URL" | aws s3 cp - "s3://${BUCKET}/config.json" \
  --content-type application/json \
  --cache-control "no-cache, no-store, must-revalidate"

echo "Invalidating CloudFront distribution ${DIST_ID}"
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" >/dev/null

FRONTEND_URL="$(aws cloudformation describe-stacks \
  --stack-name TechBlogFrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendUrl'].OutputValue" \
  --output text)"
echo "Frontend deployed: ${FRONTEND_URL}"
