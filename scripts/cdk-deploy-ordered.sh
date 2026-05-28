#!/usr/bin/env bash
# Ordered CDK deploy to avoid CloudFormation cross-stack export deadlocks.
#
# Problem: an older TechBlogApiStack imported TechBlogLambdaStack's SharedLayer export.
# Lambda cannot publish a new layer version (or remove that export) while the import exists.
#
# Fix in code: authorizer layer is built inside TechBlogApiStack (same layer_bundle asset).
# Deploy order: update Api first (drops import), then Lambda (updates layer freely).
#
# IMPORTANT: Api/Lambda/Warmer deploys use --exclusively. Without it, `cdk deploy
# TechBlogApiStack` also deploys TechBlogLambdaStack (stack dependency) and hits the
# SharedLayer export lock before Api can drop the import.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}/infrastructure"

CDK=(npx --yes aws-cdk@2.114.1 deploy --require-approval never)
CDK_STACK=(npx --yes aws-cdk@2.114.1 deploy --require-approval never --exclusively)

lambda_shared_layer_export_name() {
  aws cloudformation list-exports \
    --query "Exports[?starts_with(Name, 'TechBlogLambdaStack:') && contains(Name, 'SharedLayer')].Name | [0]" \
    --output text 2>/dev/null || echo "None"
}

stacks_importing_shared_layer_export() {
  local export_name="$1"
  if [[ -z "$export_name" || "$export_name" == "None" ]]; then
    return 1
  fi
  local imports
  imports=$(aws cloudformation list-imports --export-name "$export_name" --query 'Imports' --output text 2>/dev/null || true)
  [[ -n "$imports" && "$imports" != "None" ]]
}

print_shared_layer_export_status() {
  local export_name imports
  export_name=$(lambda_shared_layer_export_name)
  echo "SharedLayer export: ${export_name}"
  if [[ -z "$export_name" || "$export_name" == "None" ]]; then
    echo "  (none — safe to deploy TechBlogLambdaStack)"
    return
  fi
  imports=$(aws cloudformation list-imports --export-name "$export_name" --query 'Imports' --output text 2>/dev/null || echo "")
  if [[ -z "$imports" || "$imports" == "None" ]]; then
    echo "  Importers: none — safe to deploy TechBlogLambdaStack"
  else
    echo "  Importers: ${imports}"
  fi
}

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

ensure_no_shared_layer_imports() {
  local export_name attempt=1
  export_name=$(lambda_shared_layer_export_name)
  if ! stacks_importing_shared_layer_export "$export_name"; then
    echo "OK: no stack imports Lambda SharedLayer export."
    return 0
  fi

  while stacks_importing_shared_layer_export "$export_name"; do
    if [[ "$attempt" -gt 3 ]]; then
      echo "ERROR: stacks still import ${export_name} after 3 exclusive Api deploy attempts."
      print_shared_layer_export_status
      echo "Run manually: bash scripts/drop-shared-layer-import.sh"
      exit 1
    fi
    echo "=== TechBlogApiStack (attempt ${attempt}: drop SharedLayer import, --exclusively --force) ==="
    "${CDK_STACK[@]}" TechBlogApiStack --force
    wait_for_stack TechBlogApiStack
    export_name=$(lambda_shared_layer_export_name)
    attempt=$((attempt + 1))
  done

  echo "OK: SharedLayer export has no importers."
}

echo "=== TechBlogDataStack, TechBlogAuthStack ==="
"${CDK[@]}" TechBlogDataStack TechBlogAuthStack

if ! aws cloudformation describe-stacks --stack-name TechBlogLambdaStack >/dev/null 2>&1; then
  echo "=== Greenfield: TechBlogLambdaStack ==="
  "${CDK[@]}" TechBlogLambdaStack
  echo "=== Greenfield: TechBlogApiStack, TechBlogWarmerStack, TechBlogFrontendStack ==="
  "${CDK_STACK[@]}" TechBlogApiStack TechBlogWarmerStack TechBlogFrontendStack
  exit 0
fi

print_shared_layer_export_status
ensure_no_shared_layer_imports

echo "=== TechBlogLambdaStack (layer + API handlers, --exclusively) ==="
"${CDK_STACK[@]}" TechBlogLambdaStack
wait_for_stack TechBlogLambdaStack

echo "=== TechBlogWarmerStack, TechBlogFrontendStack (--exclusively) ==="
"${CDK_STACK[@]}" TechBlogWarmerStack TechBlogFrontendStack

echo "=== TechBlogApiStack (final sync, --exclusively) ==="
"${CDK_STACK[@]}" TechBlogApiStack
