#!/usr/bin/env bash
# One-shot migration: stop TechBlogApiStack importing Lambda's SharedLayer export.
#
# Run this BEFORE TechBlogLambdaStack when you see:
#   Cannot update/delete export TechBlogLambdaStack:ExportsOutputRefSharedLayer...
#   as it is in use by TechBlogApiStack.
#
# Requires AWS credentials for the target account/region.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

EXPORT_QUERY="Exports[?starts_with(Name, 'TechBlogLambdaStack:') && contains(Name, 'SharedLayer')].Name | [0]"

export_name() {
  aws cloudformation list-exports \
    --query "${EXPORT_QUERY}" --output text 2>/dev/null || echo "None"
}

print_import_status() {
  local name="$1"
  echo "SharedLayer export: ${name}"
  if [[ -z "${name}" || "${name}" == "None" ]]; then
    echo "  (no export — migration not needed)"
    return 0
  fi
  echo "  Importers:"
  aws cloudformation list-imports --export-name "${name}" --output table 2>/dev/null \
    || echo "    (none)"
}

wait_for_stack() {
  local stack_name="$1"
  local status
  status=$(aws cloudformation describe-stacks --stack-name "${stack_name}" \
    --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "MISSING")
  case "${status}" in
    UPDATE_IN_PROGRESS)
      aws cloudformation wait stack-update-complete --stack-name "${stack_name}"
      ;;
    CREATE_IN_PROGRESS)
      aws cloudformation wait stack-create-complete --stack-name "${stack_name}"
      ;;
    UPDATE_ROLLBACK_FAILED)
      echo "ERROR: ${stack_name} is UPDATE_ROLLBACK_FAILED — run continue-update-rollback first."
      exit 1
      ;;
  esac
}

has_importers() {
  local name="$1"
  [[ -n "${name}" && "${name}" != "None" ]] || return 1
  local imports
  imports=$(aws cloudformation list-imports --export-name "${name}" --query 'Imports' --output text 2>/dev/null || true)
  [[ -n "${imports}" && "${imports}" != "None" ]]
}

echo "=== Build layer bundle ==="
python backend/build.py

echo "=== Deploy TechBlogApiStack only (--exclusively --force) ==="
cd infrastructure
npx --yes aws-cdk@2.114.1 deploy TechBlogApiStack \
  --require-approval never \
  --exclusively \
  --force
wait_for_stack TechBlogApiStack

name=$(export_name)
echo
print_import_status "${name}"

if has_importers "${name}"; then
  echo
  echo "ERROR: TechBlogApiStack still imports ${name}."
  echo "Check CloudFormation events for TechBlogApiStack, then re-run this script."
  exit 1
fi

echo
echo "OK: SharedLayer export has no importers. Safe to deploy TechBlogLambdaStack:"
echo "  cd infrastructure && npx cdk deploy TechBlogLambdaStack --require-approval never --exclusively"
