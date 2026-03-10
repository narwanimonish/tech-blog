#!/usr/bin/env bash
# Run this from infrastructure/ when Lambda stack fails with:
#   "Cannot delete export ... as it is in use by TechBlogApiStack"
#
# Order: 1) Deploy Lambda (with legacy), 2) Deploy API, 3) Remove legacy in code, 4) Deploy Lambda again.
# This script does steps 1 and 2. You do step 3 (edit tech_blog_lambda_stack.py) and step 4 (cdk deploy TechBlogLambdaStack) manually.

set -e
cd "$(dirname "$0")/.."

LAMBDA_STACK="stacks/tech_blog_lambda_stack.py"
if ! grep -q 'UsersDelete' "$LAMBDA_STACK"; then
  echo "ERROR: $LAMBDA_STACK does not contain the legacy Lambdas (e.g. UsersDelete)."
  echo "Add back the 'Legacy user Lambdas' and 'Legacy post Lambdas' blocks before running this script."
  exit 1
fi

echo "Step 1: Deploy Lambda stack (with legacy – no exports deleted)..."
cdk deploy TechBlogLambdaStack --require-approval broadening

echo "Step 2: Deploy API stack (switch routes to users_api / posts_api)..."
cdk deploy TechBlogApiStack --require-approval broadening

echo "Done. Next: remove the legacy Lambda blocks from $LAMBDA_STACK, then run: cdk deploy TechBlogLambdaStack"
