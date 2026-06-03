# Tech Blog – CDK Infrastructure

Five stacks: **TechBlogDataStack** (DynamoDB), **TechBlogAuthStack** (Cognito + zip trigger Lambdas), **TechBlogLambdaStack** (container-image API Lambdas), **TechBlogApiStack** (API Gateway + authorizer), **TechBlogFrontendStack** (React UI on S3 + CloudFront).

See **[DEPLOY.md](DEPLOY.md)** for deploy order, Docker prerequisites, and API usage.

## Prerequisites

- AWS CLI configured
- Python 3.12+ and `pip install -r requirements.txt`
- **Docker** running (CDK builds Lambda **container images** from `../backend/Dockerfile.lambda`)
- CDK bootstrapped: `cdk bootstrap`

Build the UI before frontend deploy: from repo root run `make ui-build`.

## Deploy

Recommended (handles GSI migration and stack order):

```bash
bash scripts/cdk-deploy-ordered.sh
```

Or deploy stacks individually — see [DEPLOY.md](DEPLOY.md).

## Lambda packaging

| Construct | Location | Packaging |
|-----------|----------|-----------|
| `LambdaFunction` | `services/lambda_function.py` | Default: **container image** via `DockerImageCode.from_image_asset` |
| Cognito triggers | `stacks/tech_blog_auth_stack.py` | **Zip** (`packaging="zip"`) — no shared image needed |

Images are built from `backend/Dockerfile.lambda` with build arg `SERVICE=<webservice folder>`. Handler is set per function (e.g. `runtime.users.lambda_handler`). Authorizer images also install PyJWT (`install_authorizer_deps=True`).

You do **not** need `python backend/build.py` before deploy (legacy layer workflow only).

## Useful commands

```bash
cd infrastructure
cdk ls              # list stacks
cdk synth           # synthesize (runs docker build for Lambda images)
cdk deploy --all    # deploy all stacks (prefer cdk-deploy-ordered.sh)
cdk diff
```

From repo root: `make cdk-synth`, `make test`.
