# Tech Blog Backend – Setup

## Prerequisites

- Python 3.12+
- **Docker** (running) — required for CDK to build Lambda **container images**
- AWS CLI configured (for deploy)
- CDK CLI (for deploy)

## How Lambdas are packaged

App handlers (`users`, `posts`, `cognito_login`, `authorizer`) deploy as **container images** built from `backend/Dockerfile.lambda`. Each image bundles:

- `common/` and `core/` (shared code and RBAC JSON)
- One `webservice/<service>/` handler folder
- Optional pip deps (authorizer: PyJWT)

CDK sets the handler per function via `cmd` (e.g. `runtime.users.lambda_handler`). Cognito trigger Lambdas in **TechBlogAuthStack** stay **zip-packaged** (boto3-only; no shared layer).

You do **not** run `build.py` before deploy. CDK runs `docker build` during `cdk synth` / `cdk deploy`.

## Local development

Unit tests and local imports use source trees directly:

```bash
# from repo root
export PYTHONPATH=backend
python -m pytest backend/tests -v
```

To invoke a handler locally, include `backend`, `backend/common`, `backend/core`, and the handler directory on `PYTHONPATH`, or use `PYTHONPATH=backend` and import from `webservice.<name>.runtime`.

Optional legacy zip/layer experiment (not used in production deploy):

```bash
python backend/build.py   # writes backend/layer_bundle/ — not required for CDK
```

## Deploy

From repo root (see `infrastructure/DEPLOY.md` for full order):

```bash
bash scripts/cdk-deploy-ordered.sh
```

Or from `infrastructure/`:

```bash
cdk deploy TechBlogDataStack
cdk deploy TechBlogAuthStack
cdk deploy TechBlogLambdaStack
cdk deploy TechBlogApiStack
```

Each image-based Lambda’s handler is `runtime.<module>.lambda_handler` (e.g. `runtime.posts.lambda_handler`).

## Config

- **config.json** – Per-Lambda settings (timeout, memory, reserved concurrency). Read by CDK when creating functions.
