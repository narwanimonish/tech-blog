# Tech Blog Backend – Repository Structure

**Tech Blog Backend** – REST API over AWS Lambda + API Gateway (Python 3.12, DynamoDB). Handler + service layout per module.

---

## Root

```
backend/
├── README.md                 # This file – structure and modules
├── SETUP.md                  # Setup, run, deploy (container images)
├── Dockerfile.lambda         # Shared Lambda container image recipe (CDK builds per function)
├── api-spec.yaml             # OpenAPI 3.0 spec – paths, schemas, security (single source of truth)
├── config.json               # Lambda config (timeout, memory, concurrency) – read by CDK on deploy
├── build.py                  # Optional legacy script (layer_bundle); not required for deploy
├── db/
│   └── migration/
├── scripts/
│   └── data/
├── common/                   # Shared utilities (DynamoDB, API response, RBAC)
├── core/                     # Domain services (posts, users)
└── webservice/               # Lambda handlers (runtime/); bundled into container images or zip
```

---

## Modules (in dependency order)

| Module        | Purpose |
|---------------|--------|
| **common**    | Shared utilities (DynamoDB, API response helpers) |
| **core**      | Domain services – posts, users (persistence, business logic) |
| **webservice**| Lambda handlers – request/response, validation, call core + common |

---

## Module layout (per module)

Each module follows this pattern (where applicable):

```
<module>/
├── __init__.py
├── ...                        # Package contents
└── (optional) src/main/       # If needed later
```

**webservice** (one folder per Lambda; unified API handlers + auth):

```
webservice/
├── users/                    # GET/PUT/DELETE /users, /users/{userId}, /users/{userId}/role
├── posts/                    # GET/POST/PUT/DELETE /posts, /posts/{postId}
├── authorizer/               # API Gateway custom authorizer (PyJWT)
├── cognito_login/            # POST /auth/login
├── cognito_post_authentication/
└── cognito_post_confirmation/
```

---

## Package structure by module

### common
- `common` — `dynamodb_util`, `simple_api_util`, `errors`, `error_mapper`, `role_util`
- `common.rbac_config` — JSON configs for RBAC: `service_level_permissions.json`, `consolidated_api_permissions.json`, `role_permissions.json`

### core
- `core` — package root
- `core.posts` — `service` (PostsService)
- `core.users` — `service` (UsersService)

### webservice
- **users** — unified handler for all `/users` routes.
- **posts** — unified handler for all `/posts` routes.
- **authorizer**, **cognito_login** — container images (see `Dockerfile.lambda`).
- **cognito_post_*** — Cognito triggers (zip in Auth stack; boto3 only).
- Each handler lives in `runtime/<name>.py`, parses the API Gateway event, validates input, calls **core** services, and returns responses via **common**.

---

## Key paths summary

| What            | Where |
|----------------|--------|
| API spec (OpenAPI) | `api-spec.yaml` (root) |
| Lambda config  | `config.json` (root) – used by CDK for timeout, memory, reserved_concurrency |
| DB migrations  | `db/migration/` |
| Scripts / data | `scripts/`, `scripts/data/` |
| Common util    | `common/dynamodb_util.py`, `common/simple_api_util.py` |
| Posts service  | `core/posts/service.py` |
| Users service  | `core/users/service.py` |
| Handlers       | `webservice/<name>/runtime/<name>.py` |
| Container image | `Dockerfile.lambda` — `common` + `core` + one `webservice/<name>/` per function |
| RBAC config    | `common/rbac_config/*.json` (bundled in container images) |

---

## Role-based access control (RBAC)

Three access levels (aligned with service-level permissions):

- **fullaccess** — Full CRUD on the resource.
- **manage** — Create, update, delete (e.g. posts).
- **view** — Read-only.

**Roles:**

- **admin** — `users.fullaccess`, `posts.fullaccess`.
- **writer** — `users.view`, `posts.manage` (can create/update/delete posts).
- **reader** — `users.view`, `posts.view` (read-only).

User **role** is stored in the DynamoDB **users** table (`role` field). The **first user** in the table (sign-up or first successful login) gets **`admin`**; later users default to **`reader`**. Admins change roles via **`PUT /users/{userId}/role`**. Profile **`PUT /users/{userId}`** ignores `role` in the body.

**Flow:** Before handling a request, the users and posts handlers call `role_util.is_user_action_valid(event)`. That looks up the user’s role from the users table, resolves the required permission for the API path/method from `consolidated_api_permissions.json`, and checks the role’s permissions from `role_permissions.json` (with hierarchy: fullaccess ≥ manage ≥ view). If the check fails, the handler returns **403 Forbidden** with `errorCode: FORBIDDEN`.

Config files (in `common/rbac_config/`, shipped inside each container image):

- **service_level_permissions.json** — Defines services (users, posts) and their actions per level.
- **consolidated_api_permissions.json** — Maps API path + method to required permission(s).
- **role_permissions.json** — Maps each role to its service-level permissions.

---

## Build & deploy

Lambdas deploy as **container images** from `backend/Dockerfile.lambda`. Each image includes `common/`, `core/`, and one handler under `webservice/`. CDK runs `docker build` during `cdk synth` / `cdk deploy` — **Docker must be running**.

| Function | Packaging | Stack |
|----------|-----------|--------|
| `users_api`, `posts_api`, `auth_login` | Container image | TechBlogLambdaStack |
| `api-authorizer` | Container image (+ PyJWT) | TechBlogApiStack |
| Cognito post-confirmation / post-authentication | Zip | TechBlogAuthStack |

From repo root:

```bash
bash scripts/cdk-deploy-ordered.sh
```

For local tests: `PYTHONPATH=backend make test`. Optional legacy layer bundle (not used in deploy): `python backend/build.py`.

---

## Postman API Guide

Import the version-controlled collection from **`postman/collections/tech-blog-api.postman_collection.json`**. For smoke and performance runs from the CLI, see **`postman/README.md`** (`make postman-smoke`, `make postman-perf`).

Use this section to call every API from Postman.

### Postman environment variables

Create a Postman environment and add:

- `baseUrl` = `https://<api-id>.execute-api.<region>.amazonaws.com/dev`
- `accessToken` = (set after calling `/auth/login`)
- `userId` = (optional, for `/users/{userId}`)
- `postId` = (optional, for `/posts/{postId}`)

### Authorization setup

- For protected APIs, use **Authorization** tab:
  - Type: `Bearer Token`
  - Token: `{{accessToken}}`
- `POST /auth/login` is public (no bearer token required).

### 1) Login

#### `POST {{baseUrl}}/auth/login`

**Body** (raw JSON):

```json
{
  "username": "utkarsh.tehlan+1@cloudwick.com",
  "password": "YourPassword123!"
}
```

**200 Response**:

```json
{
  "accessToken": "eyJ...",
  "idToken": "eyJ...",
  "refreshToken": "eyJ...",
  "expiresIn": 3600,
  "tokenType": "Bearer"
}
```

Set `accessToken` environment variable from `accessToken` in this response.

### 2) Users APIs (Bearer required)

#### `GET {{baseUrl}}/users`

**200 Response**:

```json
{
  "items": [
    {
      "userId": "5418f4c8-40d1-7024-8d83-e627f08e1344",
      "email": "utkarsh.tehlan+1@cloudwick.com",
      "name": "Utkarsh",
      "role": "reader"
    }
  ]
}
```

#### `GET {{baseUrl}}/users/{{userId}}`

**200 Response**:

```json
{
  "userId": "5418f4c8-40d1-7024-8d83-e627f08e1344",
  "email": "utkarsh.tehlan+1@cloudwick.com",
  "name": "Utkarsh",
  "role": "reader"
}
```

**404 Response**:

```json
{
  "message": "User not found"
}
```

#### `PUT {{baseUrl}}/users/{{userId}}` (profile only)

Updates **email** and **name** only. A **`role`** field in the body is **not** applied (use **`PUT .../role`** below).

**Body** (raw JSON):

```json
{
  "email": "utkarsh.tehlan+1@cloudwick.com",
  "name": "Utkarsh Updated"
}
```

**200 Response**:

```json
{
  "email": "utkarsh.tehlan+1@cloudwick.com",
  "name": "Utkarsh Updated",
  "userId": "5418f4c8-40d1-7024-8d83-e627f08e1344"
}
```

#### `PUT {{baseUrl}}/users/{{userId}}/role` (admin only)

Sets the user’s **role** to **`admin`**, **`writer`**, or **`reader`** (any transition). Caller must have **users.fullaccess** (typically the **admin** role). See `api-spec.yaml` for the full schema.

**Body** (raw JSON):

```json
{
  "role": "writer"
}
```

**200 Response** (full user record after update):

```json
{
  "userId": "5418f4c8-40d1-7024-8d83-e627f08e1344",
  "email": "utkarsh.tehlan+1@cloudwick.com",
  "name": "Utkarsh",
  "role": "writer"
}
```

**403 Response** (non-admin):

```json
{
  "errorCode": "FORBIDDEN",
  "message": "Insufficient permission: requires users.fullaccess",
  "requestId": "..."
}
```

#### `DELETE {{baseUrl}}/users/{{userId}}`

**200 Response**:

```json
{
  "message": "Deleted"
}
```

### 3) Posts APIs (Bearer required)

#### `GET {{baseUrl}}/posts`

**200 Response**:

```json
{
  "items": [
    {
      "postId": "f9f6c9bc-19f4-4efe-9b94-6fe1a4e1f95a",
      "title": "My first post",
      "body": "Hello world"
    }
  ]
}
```

#### `POST {{baseUrl}}/posts`

**Body** (raw JSON):

```json
{
  "title": "My first post",
  "body": "Hello world"
}
```

**200 Response**:

```json
{
  "title": "My first post",
  "body": "Hello world",
  "postId": "f9f6c9bc-19f4-4efe-9b94-6fe1a4e1f95a"
}
```

#### `GET {{baseUrl}}/posts/{{postId}}`

**200 Response**:

```json
{
  "postId": "f9f6c9bc-19f4-4efe-9b94-6fe1a4e1f95a",
  "title": "My first post",
  "body": "Hello world"
}
```

**404 Response**:

```json
{
  "message": "Post not found"
}
```

#### `PUT {{baseUrl}}/posts/{{postId}}`

**Body** (raw JSON):

```json
{
  "title": "Updated title",
  "body": "Updated body"
}
```

**200 Response**:

```json
{
  "title": "Updated title",
  "body": "Updated body",
  "postId": "f9f6c9bc-19f4-4efe-9b94-6fe1a4e1f95a"
}
```

#### `DELETE {{baseUrl}}/posts/{{postId}}`

**200 Response**:

```json
{
  "message": "Deleted"
}
```

### Common error responses

- `400`: invalid request body/path parameters (e.g. invalid `role` on **`PUT .../role`**)
- `401`: missing/invalid bearer token (or bad login credentials in `/auth/login`)
- `403`: user not confirmed (login), or **RBAC** denied (e.g. non-admin calling **`PUT .../role`** or insufficient permission for the route)
- `404`: user or post not found (and similar)
- `500`: internal server error
