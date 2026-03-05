# Tech Blog Backend – Repository Structure

**Tech Blog Backend** – REST API over AWS Lambda + API Gateway (Python 3.12, DynamoDB). Handler + service layout per module.

---

## Root

```
backend/
├── README.md                 # This file – structure and modules
├── SETUP.md                  # Setup, run, deploy
├── config.json               # Lambda config (timeout, memory, concurrency)
├── build.py                  # Build script – bundles common + core into each Lambda package
├── db/
│   └── migration/
├── scripts/
│   └── data/
├── common/                   # emsflow-common
├── core/                     # core-posts + core-users
└── webservice/               # Lambda handlers (API layer)
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

**webservice** (one deployable package per Lambda):

```
webservice/
├── posts_get/
│   ├── runtime/
│   │   └── posts_get.py       # Handler; after build: common/, core/ copied here
│   └── (build adds: common/, core/)
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
| Build script   | `build.py` – bundles common + core into each `webservice/<name>/` for deployment |

---

## Build

From repo root (or `backend/`):

```bash
# 1. Bundle common + core into each Lambda package (required before deploy)
python build.py

# 2. Deploy (from infrastructure/)
cd ../infrastructure && cdk deploy
```

Run a specific Lambda locally (e.g. with a test event): use the built package under `webservice/<name>/` and set `PYTHONPATH` to that directory so that `runtime/<name>.lambda_handler` can import `common` and `core`.
