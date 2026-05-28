#!/usr/bin/env bash
# Check why the UI shows "API unavailable" (502/network errors on protected routes).
# Run from repo root with AWS credentials configured.
set -euo pipefail

EXPORT_QUERY="Exports[?starts_with(Name, 'TechBlogLambdaStack:') && contains(Name, 'SharedLayer')].Name | [0]"

echo "=== AWS identity ==="
aws sts get-caller-identity --output table

echo
echo "=== Stack status ==="
for stack in TechBlogDataStack TechBlogAuthStack TechBlogLambdaStack TechBlogApiStack TechBlogWarmerStack TechBlogFrontendStack; do
  status=$(aws cloudformation describe-stacks --stack-name "$stack" \
    --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "MISSING")
  printf "  %-24s %s\n" "$stack" "$status"
done

echo
echo "=== SharedLayer export lock ==="
EXPORT=$(aws cloudformation list-exports \
  --query "${EXPORT_QUERY}" --output text 2>/dev/null || echo "None")
echo "Export: ${EXPORT}"
if [[ -n "${EXPORT}" && "${EXPORT}" != "None" ]]; then
  aws cloudformation list-imports --export-name "${EXPORT}" --output table 2>/dev/null || echo "  (no importers)"
  echo
  echo "If TechBlogApiStack is listed: run  bash scripts/drop-shared-layer-import.sh"
fi

echo
echo "=== API smoke tests ==="
API_URL=$(aws cloudformation describe-stacks \
  --stack-name TechBlogApiStack \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text 2>/dev/null || echo "")
API_URL="${API_URL%/}"
if [[ -z "${API_URL}" || "${API_URL}" == "None" ]]; then
  echo "  (TechBlogApiStack ApiUrl output not found)"
else
  echo "  ApiUrl: ${API_URL}"
  code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}posts" || echo "000")
  echo "  GET /posts (no token): HTTP ${code}  (expect 401 or 403 if API + authorizer are up)"
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_URL}auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"x","password":"y"}' || echo "000")
  echo "  POST /auth/login (bad creds): HTTP ${code}  (expect 401/400 if login Lambda is up)"
fi

echo
echo "=== Recent authorizer failures (CloudWatch) ==="
LOG_GROUP="/aws/lambda/tech-blog-api-authorizer"
if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --query 'logGroups[0].logGroupName' --output text 2>/dev/null | grep -q authorizer; then
  aws logs filter-log-events \
    --log-group-name "$LOG_GROUP" \
    --filter-pattern "?ERROR ?Error ?Exception ?ImportModuleError ?deny" \
    --limit 5 \
    --query 'events[*].message' \
    --output text 2>/dev/null | head -20 || echo "  (no recent error lines)"
else
  echo "  Log group not found: ${LOG_GROUP}"
fi

echo
echo "=== Fix (typical order) ==="
echo "  1. bash scripts/drop-shared-layer-import.sh   # if Api still imports SharedLayer export"
echo "  2. bash scripts/cdk-deploy-ordered.sh         # full ordered deploy"
echo "  3. make ui-deploy                             # refresh config.json + UI on S3"
