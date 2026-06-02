# Deploy Tech Blog (four stacks)

Deployment is split into four stacks. Auth uses a **custom Lambda authorizer** (not the built-in Cognito authorizer) that validates the Cognito Access Token via `GetUser`.

## Stacks (deploy in order)

| Stack | Contents |
|-------|----------|
| **TechBlogDataStack** | DynamoDB tables (users, posts). Deploy first. |
| **TechBlogAuthStack** | Cognito User Pool + App Client + Hosted UI domain + Post-confirmation Lambda (populates users table). Depends on Data. |
| **TechBlogLambdaStack** | Unified users/posts/auth-login Lambdas (container images). Depends on Data and Auth. |
| **TechBlogApiStack** | API Gateway, custom Lambda authorizer, all routes. Depends on Lambda. |
| **TechBlogFrontendStack** | React SPA on S3 + CloudFront (`ui/dist`). Depends on API (for `config.json` ApiUrl). |

## Prerequisites

- AWS CLI configured (`aws configure`)
- Python 3.12+
- CDK bootstrapped (`cdk bootstrap`)

### "Unable to resolve AWS account to use"

If CDK fails with this error, either:

**Option A – Use default credentials (recommended)**  
Configure AWS and verify the CLI sees your account:

```bash
aws configure
aws sts get-caller-identity
```

Use the same terminal (or ensure your shell loads `~/.aws/credentials`) when running `cdk deploy`.

**Option B – Set account and region explicitly**  
If you use a profile or credentials that CDK doesn’t pick up, set:

```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1   # or your region
cdk deploy --all
```

Or pass them inline: `AWS_ACCOUNT_ID=123456789012 AWS_REGION=us-east-1 cdk deploy --all`

## 1. Prerequisites for Lambda container images

Lambdas deploy as **container images** built from `backend/Dockerfile.lambda`. CDK runs `docker build` during `cdk synth` / `cdk deploy`.

- Docker installed and running (Docker Desktop on macOS/Windows; Docker Engine on Linux)
- On Apple Silicon, CDK builds for `linux/amd64` automatically

Optional legacy zip/layer workflow: `python backend/build.py` (not required for deploy).

## 1b. Build frontend

From repo root:

```bash
cd ui
npm ci
npm run build
```

Or `make ui-build`. CDK only creates the S3 bucket and CloudFront distribution; upload assets with `make ui-deploy` (see below).

## 2. Install CDK dependencies

```bash
cd infrastructure
pip install -r requirements.txt
```

## 3. Deploy (all stacks in order)

```bash
cd infrastructure
cdk deploy --all
```

Or one by one:

```bash
cdk deploy TechBlogDataStack
cdk deploy TechBlogAuthStack
cdk deploy TechBlogLambdaStack
cdk deploy TechBlogApiStack
```

CDK will respect dependencies (Data → Auth → Lambda → Api → Frontend infra). Approve IAM changes when prompted. Docker builds one image per Lambda function on first deploy.

Upload the built UI to S3 and invalidate CloudFront:

```bash
make ui-deploy
```

### Deploy order script

CI and local full deploys use:

```bash
bash scripts/cdk-deploy-ordered.sh
```

This handles the posts-table GSI two-phase migration, then deploys Auth → Lambda → Api → Warmer/Frontend, and runs the posts GSI backfill.

### Zip → container image migration (custom function names)

Switching from zip Lambdas to container images **replaces** each function. If `function_name` is set explicitly, CloudFormation cannot replace in place — deploy fails with *"Rename … and update the stack again"*.

**Fix:** new physical names with the `-img` suffix via `lambda_function_name()` (e.g. `tech-blog-auth-login-img`). Keep the **same CDK construct ids** (`AuthLogin`, `UsersApi`, …) so cross-stack exports used by `TechBlogApiStack` and `TechBlogWarmerStack` are updated in place — do **not** rename constructs to `*Img` or CloudFormation tries to delete exports still imported by other stacks.

Push and redeploy. `UPDATE_ROLLBACK_COMPLETE` is safe to update again.

### Legacy: SharedLayer export errors

If upgrading from an older deployment that used Lambda **layers**, you may see CloudFormation export errors for `SharedLayer`. Run `bash scripts/drop-shared-layer-import.sh` once, then redeploy. New deployments use container images only.

### If Lambda stack fails: "Cannot delete export ... as it is in use by TechBlogApiStack" (legacy Lambdas)

The **live** API stack in AWS still imports the old Lambda exports. You must update the API stack so it stops using them, then you can remove the legacy Lambdas. Do this **exact order**:

1. **Confirm legacy block is in the Lambda stack**  
   Open `stacks/tech_blog_lambda_stack.py` and ensure the "Legacy user Lambdas" and "Legacy post Lambdas" blocks are present (the `_users_get`, `_users_delete`, `_posts_post`, etc. definitions). Do **not** remove them until step 4.

2. **Deploy Lambda stack** (with legacy still in code, so no exports are deleted):
   ```bash
   cdk deploy TechBlogLambdaStack
   ```
   If this still fails with "Cannot delete export", run `cdk synth TechBlogLambdaStack` and search the generated template in `cdk.out/` for `"UsersDelete"` – if it’s missing, the deployed code may be from another branch or the file wasn’t saved.

3. **Deploy API stack** (this updates the live API to use `users_api` and `posts_api`, so it no longer uses the old exports):
   ```bash
   cdk deploy TechBlogApiStack
   ```

4. **Remove the legacy Lambdas** from `stacks/tech_blog_lambda_stack.py` (the "Legacy user Lambdas" and "Legacy post Lambdas" blocks and their IAM grants in the `for fn in (...)` loops), then deploy Lambda stack again:
   ```bash
   cdk deploy TechBlogLambdaStack
   ```

## 4. Stack outputs

- **TechBlogDataStack**: `UsersTableName`, `PostsTableName` (exported for cross-stack). Posts table includes GSI **`PostsListByCreationTime`** (`listPk`, `creation_time`) for scalable list queries.

### Posts GSI migration and backfill

DynamoDB allows **only one GSI create or delete per table update**. Deploy uses a two-phase Data stack update in `scripts/cdk-deploy-ordered.sh`:

1. `CDK_POSTS_GSI=disabled` — remove any GSI from the CloudFormation template  
2. `scripts/migrate-posts-gsi.sh` — delete orphan indexes on the live table (`PostsByCreationTime`, etc.)  
3. `CDK_POSTS_GSI=enabled` — add **`PostsListByCreationTime`** (`listPk`, `creation_time`)  
4. `scripts/backfill-posts-gsi.sh` — set `listPk=POST` on existing post items  

Manual backfill:

```bash
bash scripts/backfill-posts-gsi.sh
# or
POSTS_TABLE=tech-blog-dev-posts python3 backend/scripts/backfill_posts_gsi.py
```

- **TechBlogAuthStack**: `UserPoolId`, `UserPoolClientId`, `CognitoDomainUrl` (Hosted UI base URL; “View login page” in console uses this).
- **TechBlogApiStack**: `ApiUrl` (API Gateway base URL).
- **TechBlogFrontendStack**: `FrontendUrl` (CloudFront URL for the UI), `WebsiteBucketName`.

## 5. Using the API (custom Lambda authorizer)

All routes require a valid **Cognito Access Token** in the `Authorization` header (the custom authorizer validates it with Cognito `GetUser`):

```http
Authorization: Bearer <ACCESS_TOKEN>
```

Use the **Access Token** from Cognito (e.g. from Amplify `Auth.currentSession()` → `getIdToken()` or access token from your auth flow). The authorizer calls `cognito-idp:GetUser` to validate it.

### Create a user (Cognito)

AWS Console → Cognito → your User Pool → Create user, or use Amplify/sign-up API.

### Call the API

```bash
export API_URL="https://xxxx.execute-api.us-east-1.amazonaws.com/dev"
export TOKEN="<your-cognito-access-token>"

curl -H "Authorization: Bearer $TOKEN" "$API_URL/posts"
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Hello","body":"World"}' "$API_URL/posts"
```

### Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | /users | List users |
| GET | /users/{userId} | Get user |
| PUT | /users/{userId} | Create/update user |
| DELETE | /users/{userId} | Delete user |
| GET | /posts | List posts |
| POST | /posts | Create post |
| GET | /posts/{postId} | Get post |
| PUT | /posts/{postId} | Create/update post |
| DELETE | /posts/{postId} | Delete post |

## 6. IAM and env vars

- **TechBlogLambdaStack**: Each handler Lambda has `grant_read_write_data` on the relevant DynamoDB table(s). Env vars: `usersStoreTable`, `postsTable` (table names from Data stack).
- **TechBlogApiStack**: Authorizer Lambda has `cognito-idp:GetUser` and is invokable by API Gateway. Env: `USER_POOL_REGION`.

## 7. Frontend

- Use **User Pool ID** and **App Client ID** (from TechBlogAuthStack) with Amplify or Cognito SDK to sign in.
- Send the **Access Token** (or ID token if you switch authorizer to validate JWT) in `Authorization: Bearer <token>` to **ApiUrl**.

To add production callback URLs for Cognito, edit `constructs/cognito_auth.py` (`callback_urls`, `logout_urls`).

## 8. Environment

- **APP_ENV**: `dev` (default) or `prod`. Table and API names are prefixed with `config.APP_NAME` (`tech-blog`).

## 9. Troubleshooting

### `LogGroup` already exists (`/aws/lambda/<function-name>`)

CloudFormation fails early validation when it tries to **create** a log group that **already exists** in CloudWatch Logs. Common causes:

- The Lambda ran once and **AWS created** `/aws/lambda/<name>` automatically (not yet owned by this stack).
- A previous stack was deleted but the log groups were **retained** or left behind.
- You switched CDK from an explicit `LogGroup` to another pattern while the old group still exists.

**Fix:** Delete the conflicting log groups (you lose their log history), then redeploy `TechBlogAuthStack` (or the stack that failed):

```bash
# Replace names if your APP_NAME differs (default app name is often tech-blog)
aws logs delete-log-group --log-group-name "/aws/lambda/tech-blog-cognito-post-confirmation-img"
aws logs delete-log-group --log-group-name "/aws/lambda/tech-blog-cognito-post-authentication"
```

If other Lambdas hit the same error, delete `/aws/lambda/<exact-function-name>` from the error message, then `cdk deploy` again.
