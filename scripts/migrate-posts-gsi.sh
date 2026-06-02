#!/usr/bin/env bash
# Drop orphan posts-table GSIs one at a time (DynamoDB allows only one GSI change per update).
# Used between two-phase TechBlogDataStack deploys during GSI migration.
#
# Usage:
#   bash scripts/migrate-posts-gsi.sh
#   POSTS_TABLE=tech-blog-dev-posts bash scripts/migrate-posts-gsi.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

POSTS_TABLE="${POSTS_TABLE:-}"
if [[ -z "$POSTS_TABLE" ]]; then
  POSTS_TABLE=$(aws cloudformation describe-stacks \
    --stack-name TechBlogDataStack \
    --query "Stacks[0].Outputs[?OutputKey=='PostsTableName'].OutputValue" \
    --output text 2>/dev/null || echo "")
fi
POSTS_TABLE="${POSTS_TABLE//[[:space:]]/}"

if [[ -z "$POSTS_TABLE" || "$POSTS_TABLE" == "None" ]]; then
  echo "Could not resolve PostsTableName (set POSTS_TABLE or deploy Data stack first)" >&2
  exit 1
fi

delete_gsi_if_exists() {
  local index_name="$1"
  local existing
  existing=$(aws dynamodb describe-table --table-name "$POSTS_TABLE" \
    --query "Table.GlobalSecondaryIndexes[?IndexName=='${index_name}'].IndexName | [0]" \
    --output text 2>/dev/null || echo "None")
  existing="${existing//[[:space:]]/}"

  if [[ -z "$existing" || "$existing" == "None" ]]; then
    echo "GSI ${index_name} not present on ${POSTS_TABLE} — skip"
    return 0
  fi

  echo "Deleting GSI ${index_name} from ${POSTS_TABLE}..."
  aws dynamodb update-table \
    --table-name "$POSTS_TABLE" \
    --global-secondary-index-updates "[{\"Delete\":{\"IndexName\":\"${index_name}\"}}]" \
    >/dev/null

  while true; do
    existing=$(aws dynamodb describe-table --table-name "$POSTS_TABLE" \
      --query "Table.GlobalSecondaryIndexes[?IndexName=='${index_name}'].IndexName | [0]" \
      --output text 2>/dev/null || echo "None")
    existing="${existing//[[:space:]]/}"
    if [[ -z "$existing" || "$existing" == "None" ]]; then
      break
    fi
    echo "  waiting for ${index_name} deletion..."
    sleep 15
  done
  echo "  deleted ${index_name}"
}

echo "Migrating posts table GSIs on: ${POSTS_TABLE}"

# Remove legacy / failed deploy index names (one deletion per API call).
for legacy_index in PostsByCreationTime PostsListByCreationTime; do
  delete_gsi_if_exists "$legacy_index"
done

echo "Posts table ready for single GSI create (PostsListByCreationTime)."
