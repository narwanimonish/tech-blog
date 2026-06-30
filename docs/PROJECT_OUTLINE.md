# Tech Blog – implementation outline (with sub-points)

Checklist ordered for demos, onboarding, or summaries. Deeper RBAC detail: [IMPLEMENTATION.md §2](IMPLEMENTATION.md).

---

## 1. Project code structure

- **`backend/common/`** – Shared runtime: DynamoDB (`dynamodb_util`), HTTP/errors (`simple_api_util`, `error_mapper`, `errors`), Lambda decorators (`lambda_decorators`), RBAC (`role_util`, `rbac_config/*.json`). See [DECORATORS.md](DECORATORS.md).
- **`backend/core/`** – Domain services: `PostsService`, `UsersService`.
- **`backend/webservice/`** – One deployable folder per Lambda; **`runtime/<handler>.py`** only in the asset zip; **`common`** and **`core`** loaded from the Lambda layer.
- **`backend/api-spec.yaml`** – OpenAPI 3.0 (paths, schemas, security).
- **`backend/config.json`** – Per-Lambda timeout, memory, reserved concurrency (read by CDK).
- **`backend/build.py`** – Produces **`layer_bundle/python/{common,core}`** and removes duplicate copies from under `webservice/`.
- **`infrastructure/`** – CDK app (`app.py`), `config/` (dev/prod), reusable constructs, stacks.
- **`backend/tests/`** – Pytest: `unit/core`, `unit/common`, `unit/webservice`; `conftest.py`; [backend/tests/README.md](../backend/tests/README.md).
- **`docs/`** – `IMPLEMENTATION.md`, `TESTING.md`, this outline.
- **API surface** – REST CRUD for users and posts via API Gateway → Lambda → DynamoDB (see CDK stacks).
- **Frontend** – Not in this repo; `sonar-project.properties` still mentions frontend for future use.

---

## 2. Lambda layers and common code deployment

- **Build** – Run `python build.py` from `backend/` to populate **`layer_bundle/python/common`** and **`layer_bundle/python/core`** (skips `__pycache__` / `.pyc`).
- **CDK** – `SharedLayer` in `TechBlogLambdaStack` packages `backend/layer_bundle` and attaches it to app Lambdas.
- **Handler zips** – Contain only handler code under `runtime/`; shared libraries are **not** duplicated inside each function asset.
- **RBAC JSON** – Lives under `common/rbac_config/` and ships in the layer so all route Lambdas share the same permission files.

---

## 3. Cognito auth and Lambda authorizer

- **User Pool + app client** – Created in **`TechBlogAuthStack`**; issues JWTs for the API.
- **Cognito trigger Lambdas** – Under `backend/webservice/` (e.g. post-confirmation, post-authentication): sync users to DynamoDB, default role where applicable.
- **`cognito_login`** – Login Lambda aligned with the auth paths in OpenAPI / `backend/README.md`.
- **Custom Lambda authorizer** – Defined in **`TechBlogApiStack`**: validates **Cognito JWT** before the request hits users/posts Lambdas; puts **`sub`** (and related context) on **`requestContext.authorizer`**.
- **After the authorizer** – Business Lambdas still enforce **RBAC** by path/method (see §4); the authorizer does not replace role checks.

---

## 4. RBAC

- **Roles** – **admin**, **writer**, **reader** (stored on each user in DynamoDB **`role`** field; new users default to **reader** via triggers / login upsert).
- **Permission model** – Service + level strings (e.g. `posts.manage`, `users.view`); levels **fullaccess** / **manage** / **view** with **dependencies** defined in JSON (not hardcoded ordering in Python).
- **Config files** (in layer) – `backend/common/rbac_config/`:
  - **`service_level_permissions.json`** – Services, levels, dependency expansion.
  - **`consolidated_api_permissions.json`** – Maps **path + HTTP method** → required permission(s).
  - **`role_permissions.json`** – Maps **role** → service→level; includes **`default_role`**.
- **Code entry point** – **`role_util.is_user_action_valid(event)`**: resolves normalized path, loads user role from the users table, expands effective permissions, returns allow or deny message.
- **Handlers** – Users and posts **`runtime`** modules call RBAC at the start; on deny return **403** with standard error shape (`FORBIDDEN`, `requestId`, etc.).
- **Posts Lambda IAM** – Read access to **users** table for role lookup during RBAC.

---

## 5. Unit testing

- **Tooling** – **pytest** in `infrastructure/requirements-dev.txt`.
- **Run (repo root)** – `PYTHONPATH=backend python -m pytest backend/tests -v` (see [backend/tests/README.md](../backend/tests/README.md)).
- **`unit/core/`** – `PostsService` / `UsersService` with **`mock_table`** (fake DynamoDB).
- **`unit/common/`** – e.g. `error_mapper` and other shared helpers.
- **`unit/webservice/`** – Handler tests with **`patch`** on `SERVICE` and RBAC; **`sys.path`** adjusted to import each Lambda’s **`runtime`** package.
- **Import-time AWS** – Handlers create `boto3.resource("dynamodb")` at module import; CI and local runs should set **`AWS_DEFAULT_REGION`** (or equivalent) so collection succeeds; tests do not call real AWS when mocks apply.

---

## 6. CDK constructs developed

- **`TechBlogDataStack`** – DynamoDB **users** (`userId`) and **posts** (`postId`); names include app + env.
- **`TechBlogAuthStack`** – Cognito + triggers; depends on data stack.
- **`TechBlogLambdaStack`** – Shared layer, **`users_api`**, **`posts_api`**, **`cognito_login`**; table env vars; IAM grants to specific tables.
- **`TechBlogApiStack`** – REST API, routes, Lambda integrations, **authorizer** Lambda (avoids circular deps with the Lambda stack).
- **Reusable constructs** – `infrastructure/services/` (e.g. **`LambdaFunction`**, **`SharedLayer`**, **`DynamoDBTable`**, **`RestApiGateway`**).
- **`infrastructure/app.py`** – Synth order: **Data → Auth → Lambda → API** with explicit dependencies.
- **Other stack files** – e.g. `tech_blog_stack.py`, `api_gateway_stack.py`, `user_service_stack.py` may be legacy; confirm before relying on them vs **`TechBlog*`** stacks.

---

## 7. Linting and formatting

- **Ruff** – Root **`pyproject.toml`**: Python **3.11**, line length **130**, rules **E**, **F**, **W**, **I**.
- **CI** – **`ruff check`** and **`ruff format --check`** on **`backend/`** (see `.github/workflows/lint.yml`).
- **Excludes** – `.venv`, `cdk.out`, `frontend`, `__pycache__`, etc., per `pyproject.toml`.

---

## 8. Infrastructure configuration for environments (dev and prod)

- **`APP_ENV`** – Read when CDK loads **`infrastructure/config`**: **`prod`** → **`ProdConfig()`**, else (default) **`DevConfig()`**.
- **`DevConfig` / `ProdConfig`** – `infrastructure/config/dev.py`, `prod.py` (app name, **`ENV`** label, and other env-specific values).
- **AWS account / region for synth** – From **`CDK_DEFAULT_ACCOUNT`**, **`AWS_ACCOUNT_ID`**, **`CDK_DEFAULT_REGION`**, **`AWS_REGION`**, or AWS CLI / STS fallback in `app.py`.
- **Resource naming** – **`ENV`** in table names (and similar) so dev and prod can coexist without name clashes.

---

## 9. GitHub Actions

- **Lint** – Push to any branch (filtered paths): Python 3.11, install Ruff, check + format check on `backend/`.
- **Tests** – Push when `backend/`, `infrastructure/requirements-dev.txt`, or workflow changes: install dev deps, **`AWS_DEFAULT_REGION`**, pytest on **`backend/tests`**.
- **Deploy** – After **lint** workflow succeeds on **`main`**: OIDC to AWS (`AWS_ROLE_ARN`), CDK CLI, `pip install -r infrastructure/requirements.txt`, **`cdk deploy --all --require-approval never`**.
- **Gating note** – Deploy is tied to **lint**, not automatically to the **test** workflow; extend workflows if you want deploy blocked on pytest.

---

## 10. SonarQube

- **Repository config** – Root **`sonar-project.properties`**: project key **`tech-blog`**, sources **`backend`**, **`infrastructure`**, tests **`backend/tests`**, coverage/exclusion patterns for test paths; **`sonar.host.url`** defaults to **`http://localhost:9000`** for a local SonarQube server.
- **How to use** – Run the **SonarScanner** CLI (or your IDE plugin) against this repo with a running SonarQube instance and token/credentials as required by your setup; the properties file is the **scan configuration**, not the server itself.
- **CI** – There is **no** SonarQube step in **`.github/workflows/`** today; adding analysis would be a separate workflow (e.g. SonarCloud or self-hosted scanner + quality gate).

---

*Aligned with: `infrastructure/stacks/`, `.github/workflows/`, `sonar-project.properties`.*
