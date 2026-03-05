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
├── posts_get/
│   └── runtime/
│       └── posts_get.py       # Handler only; common + core come from Lambda Layer
├── posts_list/
├── posts_post/
├── posts_put/
├── posts_delete/
├── users_get/
├── users_list/
├── users_put/
└── users_delete/
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
- One Lambda per resource/action: `posts_get`, `posts_list`, `posts_post`, `posts_put`, `posts_delete`, `users_get`, `users_list`, `users_put`, `users_delete`
- Each has a **handler** in `runtime/<name>.py` that parses the event, validates input, calls the appropriate **core** service, and returns an API response via **common**.

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
