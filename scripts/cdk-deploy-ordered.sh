#!/usr/bin/env bash
# Ordered CDK deploy for tech-blog stacks.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}/infrastructure"

CDK=(npx --yes aws-cdk@2.114.1 deploy --require-approval never)

wait_for_stack() {
  local stack_name="$1"
  local status
  status=$(aws cloudformation describe-stacks --stack-name "$stack_name" \
    --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "MISSING")
  case "$status" in
    UPDATE_IN_PROGRESS)
      aws cloudformation wait stack-update-complete --stack-name "$stack_name"
      ;;
    CREATE_IN_PROGRESS)
      aws cloudformation wait stack-create-complete --stack-name "$stack_name"
      ;;
  esac
}

deploy_data_stack() {
  local gsi_mode="$1"
  echo "=== TechBlogDataStack (CDK_POSTS_GSI=${gsi_mode}) ==="
  CDK_POSTS_GSI="$gsi_mode" "${CDK[@]}" TechBlogDataStack
  wait_for_stack TechBlogDataStack
}

echo "=== TechBlogDataStack phase 1: drop posts GSI from stack template (if any) ==="
deploy_data_stack disabled

echo "=== Migrate posts table GSIs (remove orphan indexes on table) ==="
bash "${ROOT}/scripts/migrate-posts-gsi.sh"

echo "=== TechBlogDataStack phase 2: add PostsListByCreationTime GSI ==="
deploy_data_stack enabled

echo "=== TechBlogAuthStack ==="
"${CDK[@]}" TechBlogAuthStack

echo "=== TechBlogLambdaStack (container images) ==="
"${CDK[@]}" TechBlogLambdaStack
wait_for_stack TechBlogLambdaStack

echo "=== TechBlogApiStack ==="
"${CDK[@]}" TechBlogApiStack
wait_for_stack TechBlogApiStack

echo "=== TechBlogWarmerStack, TechBlogFrontendStack ==="
"${CDK[@]}" TechBlogWarmerStack TechBlogFrontendStack

echo "=== Backfill posts listPk (PostsListByCreationTime GSI) ==="
bash "${ROOT}/scripts/backfill-posts-gsi.sh"
