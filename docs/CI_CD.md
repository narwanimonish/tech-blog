# CI/CD (GitHub Actions)

Workflow: [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml)

## Pipeline stages

| Trigger | Lint + test | CDK synth (dev & prod) | Deploy dev | Deploy prod |
|---------|-------------|-------------------------|------------|-------------|
| Push (any branch) | Yes | Yes | Manual only | Yes (`APP_ENV=dev`) → Postman smoke + perf |
| Pull request | Yes | Yes | No | No |
| Manual **dev** | Yes | Yes | Yes → Postman | No |
| Manual **prod** | Yes | Yes | No | Yes (`APP_ENV=dev`) → Postman |

## One-time GitHub setup

1. **Repository secret** (fallback): `AWS_ROLE_ARN` — IAM role for OIDC (`token.actions.githubusercontent.com`).

2. **Environments** (Settings → Environments):

   | Environment | Purpose | Recommended |
   |-------------|---------|-------------|
   | `development` | Auto-deploy from `main`, manual dev | Secret `AWS_ROLE_ARN` → **dev** account/role |
   | `production` | Auto-deploy on every branch push (for now) | Secret `AWS_ROLE_ARN` → **prod** account/role |

   **Postman API tests** (after each deploy): add to **both** environments:

   | Secret | Purpose |
   |--------|---------|
   | `POSTMAN_USERNAME` | Cognito user email (reader or writer is fine) |
   | `POSTMAN_PASSWORD` | That user's password |

   `baseUrl` is resolved from `TechBlogApiStack` `ApiUrl` in the deploy job (no separate secret needed).

3. **OIDC trust** on each IAM role: restrict `sub` to this repo (all branches if prod deploys from feature branches).

> **Note:** Prod deploy on every branch is enabled temporarily. Re-tighten to `main` only (and optional required reviewers) before real production use.

## Deploy behaviour

- **`APP_ENV=dev`** → `DevConfig` (table names include `-dev-`).
- **`APP_ENV=prod`** → `ProdConfig` (table names include `-prod-`).

Use **separate AWS accounts** (or at minimum separate roles with scoped policies) for development vs production.

### Why deploy uses `APP_ENV=dev` for now

Existing CloudFormation stacks (`TechBlogDataStack`, etc.) were created with **`APP_ENV=dev`**. Deploying with **`APP_ENV=prod`** makes CDK try to **rename** DynamoDB tables (`tech-blog-dev-*` → `tech-blog-prod-*`) inside the same stack, which CloudFormation cannot do in place — the update rolls back with **`UPDATE_ROLLBACK_COMPLETE`**.

Until env-suffixed stack names and resource names exist in a **separate prod account**, CI deploy jobs keep **`APP_ENV=dev`**.

After each deploy, the pipeline runs:

1. **curl smoke test** — `GET /posts` without credentials (expect **401/403**).
2. **Postman / Newman** (`scripts/postman-ci.sh pipeline`):
   - **Smoke** folder — login → list posts → get post
   - **Performance** folder — 10 iterations by default (read-only)
   - JSON report uploaded as a workflow artifact (`postman-perf-*`)

Manual workflow dispatch can set **postman_perf_iterations** (`0` = smoke only). For heavier runs, use workflow **Postman performance (manual)**.

## Manual production deploy

Push any branch (after lint, test, and synth pass), or run **CI/CD Pipeline** → **Run workflow** with target **`prod`**.

## Local parity

```bash
make lint
make test
cd infrastructure && APP_ENV=dev npx aws-cdk@2.114.1 synth
```

Deploy locally only when intentional; prefer CI for shared environments.
