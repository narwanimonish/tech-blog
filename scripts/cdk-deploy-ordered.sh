#!/usr/bin/env bash
# Ordered CDK deploy to avoid CloudFormation cross-stack export deadlocks.
# Authorizer layer lives in TechBlogApiStack; Lambda stack must not export SharedLayer to Api.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}/infrastructure"

CDK=(npx --yes aws-cdk@2.114.1 deploy --require-approval never)

echo "=== TechBlogDataStack, TechBlogAuthStack ==="
"${CDK[@]}" TechBlogDataStack TechBlogAuthStack

if ! aws cloudformation describe-stacks --stack-name TechBlogLambdaStack >/dev/null 2>&1; then
  echo "=== Bootstrap TechBlogLambdaStack (greenfield) ==="
  "${CDK[@]}" TechBlogLambdaStack
fi

echo "=== TechBlogApiStack (local authorizer layer; clears stale layer import) ==="
"${CDK[@]}" TechBlogApiStack

echo "=== TechBlogLambdaStack, TechBlogWarmerStack, TechBlogFrontendStack ==="
"${CDK[@]}" TechBlogLambdaStack TechBlogWarmerStack TechBlogFrontendStack
