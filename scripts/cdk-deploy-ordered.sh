#!/usr/bin/env bash
# Ordered CDK deploy to avoid CloudFormation cross-stack export deadlocks.
#
# Problem: an older TechBlogApiStack imported TechBlogLambdaStack's SharedLayer export.
# Lambda cannot publish a new layer version (or remove that export) while the import exists.
#
# Fix in code: authorizer layer is built inside TechBlogApiStack (same layer_bundle asset).
# Deploy order: update Api first (drops import), then Lambda (updates layer freely).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}/infrastructure"

CDK=(npx --yes aws-cdk@2.114.1 deploy --require-approval never)

api_imports_lambda_shared_layer() {
  aws cloudformation get-template --stack-name TechBlogApiStack \
    --query 'TemplateBody' --output text 2>/dev/null \
    | grep -q "ExportsOutputRefSharedLayer"
}

echo "=== TechBlogDataStack, TechBlogAuthStack ==="
"${CDK[@]}" TechBlogDataStack TechBlogAuthStack

if ! aws cloudformation describe-stacks --stack-name TechBlogLambdaStack >/dev/null 2>&1; then
  echo "=== Greenfield: TechBlogLambdaStack ==="
  "${CDK[@]}" TechBlogLambdaStack
  echo "=== Greenfield: TechBlogApiStack, TechBlogWarmerStack, TechBlogFrontendStack ==="
  "${CDK[@]}" TechBlogApiStack TechBlogWarmerStack TechBlogFrontendStack
  exit 0
fi

if api_imports_lambda_shared_layer; then
  echo "=== TechBlogApiStack (drop cross-stack SharedLayer import) ==="
  "${CDK[@]}" TechBlogApiStack

  if api_imports_lambda_shared_layer; then
    echo "ERROR: TechBlogApiStack still imports TechBlogLambdaStack SharedLayer export."
    echo "Ensure authorizer uses a local SharedLayer (not lambda_stack.shared_layer), then redeploy Api."
    exit 1
  fi
  echo "OK: Api stack no longer imports Lambda SharedLayer export."
else
  echo "=== TechBlogApiStack (routine update) ==="
  "${CDK[@]}" TechBlogApiStack
fi

echo "=== TechBlogLambdaStack (layer + API handlers) ==="
"${CDK[@]}" TechBlogLambdaStack

echo "=== TechBlogWarmerStack, TechBlogFrontendStack ==="
"${CDK[@]}" TechBlogWarmerStack TechBlogFrontendStack

echo "=== TechBlogApiStack (pick up any Lambda-side changes) ==="
"${CDK[@]}" TechBlogApiStack
