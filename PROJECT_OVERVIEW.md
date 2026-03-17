# Tech-Blog – Project Overview

## What This Is

A **serverless blog backend** on AWS: REST API (API Gateway) + Lambda (Python 3.12) + Cognito (auth) + DynamoDB (users, posts). No frontend in this repo; the API is intended for a separate client (e.g. Amplify app).

---

## Architecture (High Level)

```
[Client] → API Gateway (REST) → Lambda Authorizer (Cognito token)
                ↓
         users_api, posts_api, auth_login Lambdas
                ↓
         DynamoDB (users, posts)
```

- **Auth:** Cognito User Pool (email sign-in, Hosted UI). Custom Lambda authorizer validates the **Access Token** via `GetUser` and passes user attributes (e.g. `email`, `sub`) into the request context.
- **Public route:** `POST /auth/login` (username/password → tokens + user upserted to DynamoDB).
- **Protected routes:** All `/users` and `/posts` endpoints require `Authorization: Bearer <access_token>`.

---

## Repo Layout

| Area | Path | Notes |
|------|------|--------|
| Backend | `backend/` | Lambdas, shared layer, core services, common utils |
| Infra | `infrastructure/` | CDK (Python), stacks + constructs |
| Docs | Root + `backend/README.md`, `infrastructure/DEPLOY.md` | Feature list, API guide, deploy order |

**Backend:** `webservice/` (Lambda handlers), `core/` (UsersService, PostsService), `common/` (dynamodb_util, simple_api_util, errors, error_mapper), `layer_bundle/` (built from common + core).  
**Infrastructure:** Four stacks – Data (DynamoDB) → Auth (Cognito + triggers) → Lambda (layer + handlers) → API (Gateway + authorizer). Config in `infrastructure/config/` (base, dev, prod).

---

## Data Model

- **Users table:** `userId` (PK), `email`, optional `name`. Populated by post-confirmation trigger and by `POST /auth/login` upsert.
- **Posts table:** `postId` (PK), `title`, `body`, `creation_time` (ISO UTC), `created_by` (creator email). Set in `PostsService.create_post`; preserved on update.

---

## What’s Working Well

- Clear split between **handler** (HTTP/event) and **service** (business logic).
- **Unified Lambdas** for users and posts (one handler per resource).
- **Centralized errors:** `AppError`, `error_mapper`, `build_error_from_exception` with `requestId` and stable `errorCode`s.
- **CDK stacks** and dependencies are ordered and documented (Data → Auth → Lambda → API).
- **Postman-style API docs** in `backend/README.md` (env vars, sample requests/responses).

---

## What Can Be Done Better

Prioritized by impact and effort.

### 1. **Testing (high impact)**

- **Current:** No unit or integration tests; `pytest` is in `requirements-dev.txt` but unused.
- **Improve:** Add unit tests for `PostsService` / `UsersService` (e.g. create_post sets `creation_time`/`created_by`, update preserves them). Add tests for `error_mapper` and `simple_api_util`. Optionally integration tests against local DynamoDB or a test stack. Add a CI job (e.g. GitHub Actions) that runs tests on push/PR.

### 2. **Security (high impact)**

- **Token logging:** `cognito_login` logs the full token payload (Access/Id/Refresh). **Remove or redact** in production (e.g. log only presence/length, never the token value).
- **CORS:** API stack uses `allowed_origins=["*"]`. **Restrict** to the real frontend origin(s) in production.
- **Input validation:** No schema or length limits on `title`, `body`, `name`, `email`. **Add** validation (e.g. Pydantic or JSON Schema) and reject oversized or invalid input to reduce risk of abuse and stored XSS when rendered by a frontend.

### 3. **Config and infra consistency (medium impact)**

- **config.json** is now **wired**: `infrastructure/lambda_config.py` loads `backend/config.json` and all stacks (Lambda, API, Auth) use it for timeout, memory_size, and reserved_concurrency per function.
- **Legacy stacks:** `tech_blog_stack.py` and `user_service_stack.py` reference handlers (`users_get`, `posts_get`, etc.) that no longer exist. **Delete** these files or move to a `/legacy` folder and document that they are unused to avoid confusion and failed deploys.

### 4. **Roles and authorization (medium impact)**

- **Current:** Root README says the authorizer “validates roles” and describes Admin/User/Guest and per-route rules (e.g. admins for write, users for own id). **In code**, the authorizer only validates the token and passes attributes; there is no role or “owner” check.
- **Improve:** Either **implement** role/attribute checks (e.g. Cognito custom attribute or group “role”, and enforce in handler or authorizer context) and document the model, or **update the README** to state that currently “any authenticated user can call any route” so behavior and docs match.

### 5. **Production readiness (medium impact)**

- **Cognito URLs:** Callback/logout URLs are localhost-only. **Add** production frontend URLs in `constructs/cognito_auth.py` (or via config) when you have a live frontend.
- **Stage and env:** API stage is fixed as `dev`. Consider **stage-specific** config (e.g. `dev` vs `prod`) and different CORS/origins per stage.
- **DynamoDB:** PITR (point-in-time recovery) is commented out in the table construct. **Enable** for production tables if you need recoverability.

### 6. **Observability and operations (lower priority)**

- **Structured logging:** Use a consistent format (e.g. JSON with `requestId`, `userId`, `action`) to simplify log search and metrics.
- **Metrics:** Add minimal custom metrics (e.g. post create/update counts, auth failures) via CloudWatch or similar if you need dashboards or alerts.
- **Health/readiness:** Optional `GET /health` (no auth) for load balancer or monitoring checks.

### 7. **API and docs (nice to have)**

- **OpenAPI:** `backend/api-spec.yaml` is the OpenAPI 3.0 spec (paths, request/response schemas, bearer auth). Use it for client generation, docs, or validation.
- **.env.example:** Add a small `.env.example` (e.g. `APP_ENV=dev`, `AWS_REGION=...`) so new contributors know which env vars exist, even if values are in CDK/config.

---

## Quick Reference

| Item | Location |
|------|----------|
| Deploy order | `infrastructure/DEPLOY.md` |
| API spec (OpenAPI 3.0) | `backend/api-spec.yaml` |
| API samples (Postman-style) | `backend/README.md` |
| Lambda config (timeout, memory, concurrency) | `backend/config.json` (read by `infrastructure/lambda_config.py`) |
| Error codes / mapping | `backend/common/error_mapper.py`, `simple_api_util.py` |
| Users CRUD | `backend/core/users/service.py`, `backend/webservice/users/runtime/users.py` |
| Posts CRUD + creation_time/created_by | `backend/core/posts/service.py`, `backend/webservice/posts/runtime/posts.py` |
| Authorizer context (e.g. email) | `backend/webservice/authorizer/runtime/authorizer.py` → `requestContext.authorizer` |

---

*Generated as a project overview; use the “What Can Be Done Better” section to prioritize next steps.*
