
## 1. Retrospective alignment (HI-DLE PALMS)

*This section maps the “Retrospective & Improvement Opportunities” (HI-DLE PALMS) to what we have implemented in tech-blog vs what remains. Intended for future refactoring, onboarding, and process improvement—not as criticism of any existing implementation.*

### 1. TESTING

| Recommendation | Tech-blog status |
|----------------|------------------|
| **API (Lambda) tests** – pytest for auth, validation, CRUD, error handling | **Not yet.** No unit or integration tests for Lambda handlers. |
| **Web app tests** – Vitest/Jest, E2E for critical flows | **N/A** – no frontend in this repo. |
| **Contract / API tests** – OpenAPI and contract/snapshot tests | **Partial.** We have `backend/api-spec.yaml` (OpenAPI 3.0). No automated contract or snapshot tests yet. |

**Next steps:** Add pytest for `role_util`, services (e.g. `UsersService`, `PostsService`), and error_mapper; add contract tests for key endpoints using the spec.

---

### 2. ERROR HANDLING AND EXCEPTIONS

| Recommendation | Tech-blog status |
|----------------|------------------|
| **Avoid broad `except Exception`** – catch specific exceptions | **Done** Handlers use a single `except Exception` that delegates to `build_error_from_exception`, which maps known types. We could narrow to `ClientError`, `AppError`, `JSONDecodeError`, etc. and re-raise the rest. |
| **Standardize error responses** – code, message, requestId | **Done.** All errors go through `simple_api_util.build_error_response` or `build_error_from_exception`. Shape: `errorCode`, `message`, `requestId` (and optional `details`). |
| **ValidationError type** – 400 with field-level details | **Done** We use `build_error_response("BAD_REQUEST", "…", 400)`. We have `AppError` and error_mapper; we could add a dedicated `ValidationError` and map it to 400 with a `details` object for fields. |

**Implemented:** `common/errors.py` (`AppError`), `common/error_mapper.py` (maps AWS, JSON, ValueError, etc. to `FrontendError`), `common/simple_api_util.py` (`build_error_response`, `build_error_from_exception`).

---

### 3. ENVIRONMENT VARIABLES AND CONFIGURATION

| Recommendation | Tech-blog status |
|----------------|------------------|
| **Centralize config loading** – fail fast if required vars missing | **Done** Handlers use `os.environ.get("…", default)`. We could add a small config module that validates required vars at cold start. |
| **No hardcoded / magic values** – shared constants | **Partial.** Table names and a few literals come from env; RBAC and API permissions are in JSON. Some defaults live in code (e.g. default_role). |
| **Sensitive data in logs** – redaction, structured logging | **Done** We log request_id and high-level flow; full token logging in `cognito_login` was intentional per request but should be removed/redacted for production. No shared structured (e.g. JSON) logger or redaction helper yet. |

**Implemented:** Lambda settings centralized in `backend/config.json` and read by CDK via `infrastructure/lambda_config.py`.

---

### 4. CODE STRUCTURE AND MAINTAINABILITY

| Recommendation | Tech-blog status |
|----------------|------------------|
| **Split very large files** – by domain or layer | **Done.** Handlers are small (users, posts); logic lives in core services and common utils. No 2,000+ line files. |
| **No duplication across Lambdas** – shared modules / layers | **Done.** DynamoDB via `common.dynamodb_util`; responses/errors via `common.simple_api_util` and `common.error_mapper`; RBAC via `common.role_util`. Shared code is in a Lambda layer (`common`, `core`). |
| **Split commonUtil** – auth, dynamodb_util, email_util, etc. | **Done.** We have focused modules: `dynamodb_util.py`, `simple_api_util.py`, `errors.py`, `error_mapper.py`, `role_util.py`. No single “commonUtil” blob. |

---

### 5. INPUT VALIDATION AND API DESIGN

| Recommendation | Tech-blog status |
|----------------|------------------|
| **Validate at the edge** – schema or Pydantic | **Done** Handlers check presence of body/path params and catch `JSONDecodeError`. No request-body schema or Pydantic validation yet. |
| **Central API schema** – OpenAPI / shared types | **Done.** `backend/api-spec.yaml` is OpenAPI 3.0 with paths, request/response schemas, and error response shape. Single source of truth for the API. |

---

### 6. SECURITY

| Recommendation | Tech-blog status |
|----------------|------------------|
| **JWT validation in one place** – API Gateway Authorizer | **Done.** Custom Lambda authorizer validates Cognito token; invalid tokens are denied before reaching business Lambdas. |
| **Least privilege** – no wildcard DynamoDB ARNs | **Done.** CDK grants `grant_read_write_data` / `grant_read_data` on specific table constructs; posts_api has read-only on users table for RBAC lookup. |

---

### 7. DOCUMENTATION

| Recommendation | Tech-blog status |
|----------------|------------------|
| **API docs** – generate from Swagger UI | **Done** OpenAPI spec exists; no Swagger UI or generated docs in the repo yet. |
| **Docstrings for public functions** | **Done** Key modules (dynamodb_util, simple_api_util, error_mapper, role_util) have docstrings; coverage is not enforced by lint. |

---

### 8. INFRASTRUCTURE AND DEVOPS

| Recommendation | Tech-blog status |
|----------------|------------------|
| **Replace wildcard ARNs** | **Done.** No wildcard DynamoDB ARNs; authorizer uses `*` for Cognito (required for GetUser). |
| **CI/CD pipeline** – lint and test | **Not yet.** No `.github/workflows` or `.gitlab-ci.yml` in repo. `requirements-dev.txt` includes pytest but tests are not run in CI. |

---

### 9. Summary of priorities (aligned with retrospective)

| Priority | What we implemented | What remains |
|----------|--------------------|--------------|
| **High impact** | Standardized error responses (code, message, requestId); shared error mapper; centralized Lambda config; authorizer so invalid tokens don’t reach Lambdas; least-privilege table grants. | Unit tests for critical Lambda paths; centralize env validation and fail fast; remove/redact token logging in production. |
| **Medium term** | Split structure (handlers / services / common); no big “commonUtil” (focused modules); OpenAPI spec; RBAC with config-driven permissions. | Request validation (e.g. Pydantic/schema); dedicated ValidationError and field-level 400; structured JSON logging; docstring/lint rules; CI pipeline for lint and test; Swagger UI or generated API docs. |
| **Lower** | — | Contract/snapshot tests against OpenAPI; E2E if/when a frontend is added. |

---

## 2. RBAC implementation – how we achieve it

*Single dedicated point: end-to-end role-based access control.*

### Goal

Before running any business logic, we ensure the authenticated user’s **role** has the **permission** required for that API (path + method). Roles: **admin**, **writer**, **reader**. Permissions are expressed as service + level: **fullaccess**, **manage**, **view** (e.g. `posts.manage`, `users.view`).

### How we achieve it

1. **Where the user’s role lives**  
   The user’s **role** is stored in the DynamoDB **users** table (`role` field). New users get default role **reader** (set in Cognito post-confirmation and preserved on login upsert). To grant admin/writer, update that user’s `role` in the users table.

2. **Three config files (data-driven)**  
   All under `backend/common/rbac_config/` (shipped in the Lambda layer):

   | File | Purpose |
   |------|----------|
   | **service_level_permissions.json** | Defines each service (users, posts) and its levels (fullaccess, manage, view). Each level can list **dependencies** (e.g. fullaccess → manage, view; manage → view). The logic uses these to compute “effective” permissions. |
   | **consolidated_api_permissions.json** | Maps **API path + HTTP method** to the **required permission(s)** (e.g. `GET /posts` → `["posts.view"]`, `POST /posts` → `["posts.manage"]`). |
   | **role_permissions.json** | Maps **role name** to **service → level** (e.g. admin: users.fullaccess, posts.fullaccess; writer: users.view, posts.manage; reader: users.view, posts.view). |

3. **Single entry point in code: `role_util.is_user_action_valid(event)`**  
   Handlers (users, posts) call this **before** doing any work. It:

   - Reads **path** and **httpMethod** from the API Gateway event (and normalizes path, e.g. `/users/abc-123` → `/users/{userId}`).
   - Resolves **user id** from `event.requestContext.authorizer` (Cognito `sub` or `principalId` set by our custom authorizer).
   - Loads the user’s **role** from the DynamoDB users table (env: `usersStoreTable`). If the user or role is missing, uses **default_role** from `role_permissions.json` (reader).
   - Gets **required permissions** for this path + method from `consolidated_api_permissions.json`.
   - Gets the **role’s** service→level from `role_permissions.json`, then **expands** it to a set of effective permission strings using **dependencies** from `service_level_permissions.json` (e.g. role “writer” has `posts.manage` → effective set includes `posts.manage` and `posts.view`).
   - Checks that every required permission is in that effective set.
   - Returns `(True, "")` if allowed, or `(False, "Insufficient permission: requires ...")` if denied.

4. **Handler contract**  
   If `is_user_action_valid` returns not allowed, the handler immediately returns **403** with our standard error shape: `errorCode: FORBIDDEN`, `message` (the string from role_util), and `requestId`. No business logic runs.

5. **Why dependencies matter**  
   We do **not** hardcode “fullaccess ≥ manage ≥ view” in Python. Instead, we read **dependancies** (or **dependencies**) from `service_level_permissions.json`. So “writer” with `posts.manage` automatically gets `posts.view` as well, and “admin” with `posts.fullaccess` gets `posts.manage` and `posts.view`. Adding a new level or cross-service rule is a config change, not a code change.

### Flow (summary)

```
Request → Authorizer (validates JWT, passes sub in context)
       → Lambda handler
       → role_util.is_user_action_valid(event)
            → get user id from event
            → get role from DynamoDB users table
            → get required permission(s) for path + method from consolidated_api_permissions.json
            → get role’s service→level from role_permissions.json
            → expand to effective permissions using service_level_permissions.json dependencies
            → required ⊆ effective?
       → if no: return 403 FORBIDDEN
       → if yes: run business logic (service layer, dynamodb_util, etc.)
```

### Files involved

| What | Where |
|------|--------|
| RBAC logic | `backend/common/role_util.py` (`is_user_action_valid`, `_expand_effective_permissions`, `_get_dependencies_for_level`, etc.) |
| RBAC config | `backend/common/rbac_config/*.json` |
| Usage in handlers | `backend/webservice/users/runtime/users.py`, `backend/webservice/posts/runtime/posts.py` (call `role_util.is_user_action_valid` at top; on False, return 403) |
| User role storage | DynamoDB **users** table, field `role` (admin | writer | reader) |
| Default role for new users | Set in post-confirmation Lambda and login upsert; default_role in `role_permissions.json` is **reader** |
