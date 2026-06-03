# Tech Blog

Serverless REST API (AWS Lambda + API Gateway + DynamoDB + Cognito) with a React UI.

## Architecture

| Layer | Location | Notes |
|-------|----------|--------|
| API | `backend/webservice/` | Unified `users` and `posts` handlers; Cognito login + authorizer |
| Domain | `backend/core/` | `UsersService`, `PostsService` |
| Shared | `backend/common/` | DynamoDB helpers, RBAC, API responses |
| Infra | `infrastructure/` | CDK — Data → Auth → Lambda → API → Frontend |
| UI | `ui/` | Vite + React SPA |

**Lambda packaging:** App functions use **container images** (`backend/Dockerfile.lambda`) with `common`, `core`, and handler code in one image. Cognito trigger Lambdas use zip deploy. See [backend/README.md](backend/README.md) and [infrastructure/README.md](infrastructure/README.md).

## Quick start

```bash
pip install -r infrastructure/requirements-dev.txt
make test
bash scripts/cdk-deploy-ordered.sh   # needs AWS creds + Docker
make ui-deploy                       # after CDK frontend stack exists
```

## Docs

- [backend/README.md](backend/README.md) — API, RBAC, handlers
- [backend/SETUP.md](backend/SETUP.md) — local dev and deploy
- [infrastructure/DEPLOY.md](infrastructure/DEPLOY.md) — stack order and troubleshooting
- [postman/README.md](postman/README.md) — API smoke / performance tests
- [ui/README.md](ui/README.md) — frontend local dev and CloudFront deploy

## Features

- **Users** — CRUD + role management (admin / writer / reader)
- **Posts** — CRUD with pagination
- **Auth** — Cognito sign-up/login; custom Lambda authorizer on API routes
- **First user** — automatically assigned `admin` in DynamoDB
