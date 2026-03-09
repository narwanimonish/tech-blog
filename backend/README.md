# Tech Blog Backend – Repository Structure

**Tech Blog Backend** – REST API over AWS Lambda + API Gateway (Python 3.12, DynamoDB). Handler + service layout per module.

---

## Root

```
backend/
├── README.md                 # This file – structure and modules
├── SETUP.md                  # Setup, run, deploy
├── config.json               # Lambda config (timeout, memory, concurrency)
├── build.py                  # Build script – creates layer_bundle for Lambda Layer
├── db/
│   └── migration/
├── scripts/
│   └── data/
├── common/                   # Shared utilities (DynamoDB, API response)
├── core/                     # Domain services (posts, users)
├── layer_bundle/             # Build output: python/common, python/core (for Lambda Layer)
└── webservice/               # Lambda handlers only (runtime/); common + core via Layer
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

**webservice** (one folder per Lambda; each contains only the handler):

```
webservice/
├── posts/
│   └── runtime/
│       └── posts.py           # Unified posts handler (GET/POST/GET by id/PUT/DELETE)
├── users/
│   └── runtime/
│       └── users.py           # Unified users handler (GET list/GET by id/PUT/DELETE)
├── authorizer/
├── cognito_login/
├── cognito_post_authentication/
└── cognito_post_confirmation/
```

---

## Package structure by module

### common
- `common` — `dynamodb_util`, `simple_api_util`

### core
- `core` — package root
- `core.posts` — `service` (PostsService)
- `core.users` — `service` (UsersService)

### webservice
- Unified lambdas: `posts` and `users` handle all methods/routes for their resource.
- Auth-related lambdas: `authorizer`, `cognito_login`, `cognito_post_authentication`, `cognito_post_confirmation`.
- Each has a **handler** in `runtime/<name>.py` that parses the event, validates input, calls **core** services, and returns an API response via **common**.

---

## Key paths summary

| What            | Where |
|----------------|--------|
| Lambda config  | `config.json` (root) |
| DB migrations  | `db/migration/` |
| Scripts / data | `scripts/`, `scripts/data/` |
| Common util    | `common/dynamodb_util.py`, `common/simple_api_util.py` |
| Posts service  | `core/posts/service.py` |
| Users service  | `core/users/service.py` |
| Handlers       | `webservice/<name>/runtime/<name>.py` |
| Layer bundle   | `build.py` → `layer_bundle/python/{common,core}` (Lambda Layer; no copy per handler) |

---

## Build

Common and core live **once** in a Lambda Layer; they are not copied into each webservice folder.

From `backend/`:

```bash
# 1. Build the layer (creates layer_bundle/python/{common,core})
python build.py

# 2. Deploy (from infrastructure/) – layer is attached to every Lambda
cd ../infrastructure && cdk deploy
```

Each Lambda’s asset is only `webservice/<name>/` (just `runtime/`). The layer supplies `common` and `core` at runtime. For local runs, set `PYTHONPATH` to include `backend/common` and `backend/core` (or the `layer_bundle/python` directory).

---

## Postman API Guide

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
      "name": "Utkarsh"
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
  "name": "Utkarsh"
}
```

**404 Response**:

```json
{
  "message": "User not found"
}
```

#### `PUT {{baseUrl}}/users/{{userId}}`

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

- `400`: invalid request body/path parameters
- `401`: missing/invalid bearer token (or bad login credentials in `/auth/login`)
- `403`: user not confirmed (login flow)
- `500`: internal server error
