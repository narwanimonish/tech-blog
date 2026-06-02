#!/usr/bin/env bash
# Set listPk=POST on existing posts so they appear in PostsListByCreationTime GSI.
# Idempotent — safe to run every deploy.
#
# Usage (from repo root, AWS credentials configured):
#   bash scripts/backfill-posts-gsi.sh
#   POSTS_TABLE=tech-blog-dev-posts bash scripts/backfill-posts-gsi.sh
#   bash scripts/backfill-posts-gsi.sh --dry-run
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DRY_RUN="${1:-}"

POSTS_TABLE="${POSTS_TABLE:-}"
if [[ -z "$POSTS_TABLE" ]]; then
  POSTS_TABLE=$(aws cloudformation describe-stacks \
    --stack-name TechBlogDataStack \
    --query "Stacks[0].Outputs[?OutputKey=='PostsTableName'].OutputValue" \
    --output text 2>/dev/null || echo "")
fi
POSTS_TABLE="${POSTS_TABLE//[[:space:]]/}"

if [[ -z "$POSTS_TABLE" || "$POSTS_TABLE" == "None" ]]; then
  echo "Could not resolve PostsTableName from TechBlogDataStack (set POSTS_TABLE or deploy Data stack first)" >&2
  exit 1
fi

echo "Backfilling posts GSI attributes on table: ${POSTS_TABLE}"
export POSTS_TABLE

python3 -c "import boto3" 2>/dev/null || python3 -m pip install -q boto3

if [[ "$DRY_RUN" == "--dry-run" ]]; then
  python3 "${ROOT}/backend/scripts/backfill_posts_gsi.py" --dry-run
else
  python3 "${ROOT}/backend/scripts/backfill_posts_gsi.py"
fi
