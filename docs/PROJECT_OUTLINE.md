# Tech Blog – implementation outline (with sub-points)

High-level checklist of what the repository implements. Use this for demos, onboarding, or résumé-style summaries.

---

## 1. Project code structure

- **`backend/common/`** – Shared runtime code: DynamoDB helpers (`dynamodb_util`), HTTP/error helpers (`simple_api_util`, `error_mapper`, `errors`), RBAC (`role_util`, `rbac_config/*.json`).
- **`backend/core/`** – Domain services: `PostsService`, `UsersService` (table access and business rules).
- **`backend/webservice/`** – One folder per Lambda asset: `runtime/<handler>.py` only in the zip; imports `common` and `core` from the **layer** at `/opt/python`.
- **`backend/api-spec.yaml`** – OpenAPI 3.0 description of routes, schemas, and security.
- **`backend/config.json`** – Per-function Lambda settings (timeout, memory, reserved concurrency) read by CDK.
- **`backend/build.py`** – Builds `layer_bundle/python/{common,core}` and strips duplicate copies from webservice folders.
- **`infrastructure/`** – Python CDK app (`app.py`), environment config, reusable service constructs, stacks.
- **`backend/tests/`** – Pytest layout: `unit/core`, `unit/common`, `unit/webservice`; shared `conftest.py` and `README.md`.
- **`docs/`** – Implementation notes, testing notes, this outline.
- **Frontend** – Not present in this repo (Ruff excludes a `frontend` path if added later).

---

## 2. CDK constructs developed

- **`TechBlogDataStack`** – DynamoDB tables for users (`userId`) and posts (`postId`); names include app name and env suffix.
- **`TechBlogAuthStack`** – Cognito User Pool, app client, Lambda triggers wired to user storage; depends on data stack.
- **`TechBlogLambdaStack`** – Shared Lambda layer asset, `users_api`, `posts_api`, `cognito_login` functions; IAM grants to specific tables; env vars for table names.
- **`TechBlogApiStack`** – API Gateway REST API, routes, Lambda integrations, **custom Lambda authorizer** (defined here to avoid circular dependencies with the Lambda stack).
- **Reusable constructs** (under `infrastructure/services/`) – e.g. `LambdaFunction`, `SharedLayer`, `DynamoDBTable`, `RestApiGateway`.
- **`infrastructure/app.py`** – Wires stacks in order: Data → Auth → Lambda → API, with explicit dependencies.
- **Legacy / alternate stack files** – `tech_blog_stack.py`, `api_gateway_stack.py`, `user_service_stack.py` may exist alongside the `TechBlog*` stacks; confirm whether they are still deployed or historical.

---

## 3. Lambda layers and common code deployment

- **Layer contents** – `common` and `core` copied into `backend/layer_bundle/python/` via `build.py` (excludes `__pycache__` / `.pyc`).
- **Attachment** – All app Lambdas in `TechBlogLambdaStack` use the same shared layer construct (`SharedLayer`).
- **Handler bundles** – Each webservice directory deployed as a Lambda asset contains **only** the handler code (`runtime/`); no bundled copy of `common`/`core` in the asset zip (they come from the layer).
- **RBAC config** – JSON files under `common/rbac_config/` ship inside the layer so every protected Lambda sees the same permission maps.

---

## 4. Cognito auth and Lambda authorizer

- **User Pool + client** – Provisioned in `TechBlogAuthStack`; used for sign-up, login, and JWT issuance.
- **Triggers** – Cognito-trigger Lambdas (e.g. post-confirmation, post-authentication) under `backend/webservice/` create or update users in DynamoDB and set default **role** where applicable.
- **`cognito_login`** – Login Lambda exposes tokens / session flow expected by the API (see OpenAPI and `backend/README.md`).
- **Custom API authorizer** – Validates the Cognito JWT before API Gateway forwards to route Lambdas; passes identity context (`sub`, etc.) into `requestContext.authorizer`.
- **Handler-level RBAC** – After the authorizer, users/posts handlers call `role_util.is_user_action_valid(event)` for path/method permissions (see [IMPLEMENTATION.md §2 – RBAC](IMPLEMENTATION.md)).

---

## 5. Linting and formatting

- **Ruff** – Configured in root `pyproject.toml` (Python 3.11 target, line length, rules `E`, `F`, `W`, `I`).
- **Scope** – `ruff check` and `ruff format --check` run on `backend/` in CI.
- **Excludes** – Virtual envs, `cdk.out`, `frontend`, `__pycache__`, etc., per `pyproject.toml`.

---

## 6. Infrastructure configuration for environments (dev and prod)

- **`APP_ENV`** – Environment variable read at CDK synth time (`infrastructure/config/__init__.py`): `prod` selects `ProdConfig`, anything else (default **`dev`**) selects `DevConfig`.
- **`DevConfig` / `ProdConfig`** – Separate modules under `infrastructure/config/` (e.g. app name, env label, and any env-specific constants).
- **AWS account / region** – Resolved from `CDK_DEFAULT_ACCOUNT`, `AWS_ACCOUNT_ID`, `CDK_DEFAULT_REGION`, `AWS_REGION`, or AWS CLI / STS when not set in env.
- **Table naming** – Includes `ENV` from config so dev and prod stacks can coexist without clashing on table names.

---

## 7. Unit testing

- **Runner** – `pytest` (see `infrastructure/requirements-dev.txt`).
- **How to run** – From repo root: `PYTHONPATH=backend python -m pytest backend/tests -v` (see `backend/tests/README.md`).
- **`unit/core/`** – Tests for `PostsService` and `UsersService` with a mocked DynamoDB table (`mock_table` fixture).
- **`unit/common/`** – Tests for shared utilities (e.g. `error_mapper`).
- **`unit/webservice/`** – Handler tests: patch `SERVICE` and RBAC, import `runtime.*` with `sys.path` adjusted per Lambda layout.
- **CI note** – Webservice tests need a default AWS region at **import** time (`AWS_DEFAULT_REGION`), because handlers construct `boto3.resource("dynamodb")` at module load; real AWS is not called when mocks are applied.

---

## 8. GitHub Actions

- **Lint workflow** – On push to any branch when `backend/`, `infrastructure/`, or the workflow file changes: Python 3.11, Ruff check + format check.
- **Test workflow** – On push when `backend/`, `infrastructure/requirements-dev.txt`, or the workflow changes: install dev deps, set `AWS_DEFAULT_REGION`, run pytest on `backend/tests`.
- **Deploy workflow** – Triggered after the **lint** workflow completes successfully on **`main`**; assumes AWS OIDC (`AWS_ROLE_ARN` secret), installs CDK CLI and infrastructure requirements, runs `cdk deploy --all --require-approval never`.
- **Gating** – Deploy currently depends on **lint passing**, not on the **test** workflow; you can add a `workflow_run` on tests or merge jobs if you want deploy blocked on pytest too.

---

## 9. Additional areas (cross-cutting)

- **REST API and persistence** – CRUD for users and posts via API Gateway → Lambda → DynamoDB; least-privilege IAM on specific table constructs.
- **Standard errors** – `AppError`, `error_mapper`, and `simple_api_util.build_error_response` / `build_error_from_exception` for consistent API error shape (`errorCode`, `message`, `requestId`).
- **OpenAPI as contract** – `api-spec.yaml` documents paths and schemas; no generated Swagger UI or automated contract tests in-repo yet (see [IMPLEMENTATION.md](IMPLEMENTATION.md) for gaps).
- **Documentation** – Root `README.md`, `backend/README.md` (structure, RBAC, Postman-style examples), `backend/tests/README.md`, `docs/TESTING.md`, `docs/IMPLEMENTATION.md`.

---

*Last aligned with repo layout: stacks under `infrastructure/stacks/`, workflows under `.github/workflows/`.*
