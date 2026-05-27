# CI/CD (GitHub Actions)

Workflow: [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml)

## Pipeline stages

| Trigger | Lint + test | CDK synth (dev & prod) | Deploy dev | Deploy prod |
|---------|-------------|-------------------------|------------|-------------|
| Push (any branch) | Yes | Yes | Manual only | Yes (`APP_ENV=dev`) |
| Pull request | Yes | Yes | No | No |
| Manual **dev** | Yes | Yes | Yes | No |
| Manual **prod** | Yes | Yes | No | Yes (`APP_ENV=dev`) |

## One-time GitHub setup

1. **Repository secret** (fallback): `AWS_ROLE_ARN` — IAM role for OIDC (`token.actions.githubusercontent.com`).

2. **Environments** (Settings → Environments):

   | Environment | Purpose | Recommended |
   |-------------|---------|-------------|
   | `development` | Auto-deploy from `main`, manual dev | Secret `AWS_ROLE_ARN` → **dev** account/role |
   | `production` | Auto-deploy on every branch push (for now) | Secret `AWS_ROLE_ARN` → **prod** account/role |

3. **OIDC trust** on each IAM role: restrict `sub` to this repo (all branches if prod deploys from feature branches).

> **Note:** Prod deploy on every branch is enabled temporarily. Re-tighten to `main` only (and optional required reviewers) before real production use.

## Deploy behaviour

- **`APP_ENV=dev`** → `DevConfig` (table names include `-dev-`).
- **`APP_ENV=prod`** → `ProdConfig` (table names include `-prod-`).

Use **separate AWS accounts** (or at minimum separate roles with scoped policies) for development vs production.

### Why deploy uses `APP_ENV=dev` for now

Existing CloudFormation stacks (`TechBlogDataStack`, etc.) were created with **`APP_ENV=dev`**. Deploying with **`APP_ENV=prod`** makes CDK try to **rename** DynamoDB tables (`tech-blog-dev-*` → `tech-blog-prod-*`) inside the same stack, which CloudFormation cannot do in place — the update rolls back with **`UPDATE_ROLLBACK_COMPLETE`**.

Until env-suffixed stack names and resource names exist in a **separate prod account**, CI deploy jobs keep **`APP_ENV=dev`**.

After each deploy, the pipeline runs a **smoke test**: it reads the `TechBlogApiStack` `ApiUrl` output and calls `GET /posts` without credentials. A **401 or 403** confirms API Gateway and the authorizer are reachable.

## Manual production deploy

Push any branch (after lint, test, and synth pass), or run **CI/CD Pipeline** → **Run workflow** with target **`prod`**.

## Local parity

```bash
make lint
make test
cd infrastructure && APP_ENV=dev npx aws-cdk@2.114.1 synth
```

Deploy locally only when intentional; prefer CI for shared environments.
