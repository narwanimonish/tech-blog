# Backend tests

This folder holds **pytest** unit tests for core services, Lambda handlers, and shared modules. This README traces what happens from the command you type to a passing (or failing) test.

---

## 1. Commands you run

**From the repository root (recommended):**

```bash
pip install -r infrastructure/requirements-dev.txt
PYTHONPATH=backend python -m pytest backend/tests -v
```

(`requirements-dev.txt` includes **pytest**, **boto3**, and **botocore**, which some tests need for imports such as `ClientError`.)

**From the `backend` directory:**

```bash
pip install -r ../infrastructure/requirements-dev.txt
PYTHONPATH=. python -m pytest tests -v
```

**Useful variants:**

| Goal | Example |
|------|---------|
| One file | `PYTHONPATH=backend python -m pytest backend/tests/unit/core/test_posts_service.py -v` |
| One test | `PYTHONPATH=backend python -m pytest backend/tests/unit/common/test_error_mapper.py::test_name -v` |
| Stop on first failure | `... pytest backend/tests -x` |
| Show print output | `... pytest backend/tests -s` |

---

## 2. What the shell does

1. **`python -m pytest`** – Runs pytest as a module so it uses the same Python interpreter and environment you installed packages into.

2. **`backend/tests`** – Tells pytest **where to discover tests**. It collects functions and methods whose names start with `test_` in files named `test_*.py` (under `backend/tests/`).

3. **`PYTHONPATH=backend`** – Prepends the `backend` directory to Python’s import path **for that process**. Your application code uses package-less imports such as `from common.errors import AppError` and `from core.posts.service import PostsService`, which resolve to `backend/common`, `backend/core`, etc. Without this, those imports fail with `ModuleNotFoundError`.

---

## 3. What pytest does when it starts

1. **Finds the project root** – Pytest may load settings from `pyproject.toml` at the repo root (e.g. Ruff; pytest itself uses defaults unless you add `[tool.pytest.ini_options]`).

2. **Loads `conftest.py`** – For any test under `backend/tests/`, pytest automatically loads `backend/tests/conftest.py` **before** collecting tests. That file:
   - Inserts **`backend/`** into `sys.path` (again) so imports work even if `PYTHONPATH` were forgotten in some edge cases.
   - Registers **fixtures**: `mock_table`, `mock_context`, `base_event`, and defines **`api_event(...)`** as a plain helper (also duplicated for typed use in `helpers.py`).

3. **Collects tests** – Walks `unit/core`, `unit/common`, `unit/webservice`, imports each test module, registers tests and fixtures.

4. **Runs tests** – For each test, builds any needed fixtures (e.g. a fresh `MagicMock` for `mock_table`), runs the test function, reports pass/fail.

---

## 4. How the three test areas differ

| Area | Location | What is real | What is mocked |
|------|-----------|--------------|----------------|
| **Core services** | `unit/core/` | `UsersService` / `PostsService` code | DynamoDB **Table** (`mock_table` from `conftest.py`) |
| **Common** | `unit/common/` | Pure mapping / error logic | Nothing or small exception types (e.g. `ClientError`) |
| **Webservice (handlers)** | `unit/webservice/` | Handler entrypoint (`lambda_handler`) and wiring | **SERVICE** (service layer), **RBAC** (`role_util.is_user_action_valid`), plus Lambda **context** |

**Handler tests** need one extra step: the Lambda code lives under `backend/webservice/<feature>/runtime/` and imports as `runtime.posts` or `runtime.users`. Each handler test module adds that runtime directory to **`sys.path`** and then imports `lambda_handler`. That mirrors how the zip layout works in AWS without packaging the whole repo.

---

## 5. End-to-end flow (examples)

These walk through **what runs, in order**, for two typical tests.

### 5.1 Core service test (mock DynamoDB)

**Test:** `test_get_post_returns_item` in `unit/core/test_posts_service.py`.

**Idea:** You never touch real AWS. `mock_table` is a `MagicMock` that pretends to be a DynamoDB table. You tell it what `get_item` should return; your service code runs for real on top of that fake.

**Call sequence (plain English):**

| Step | What runs | Notes |
|------|-----------|--------|
| 1 | You run pytest (see §1). | Pytest discovers `test_*` functions under `backend/tests/`. |
| 2 | Pytest loads `conftest.py`. | Adds `backend/` to `sys.path`, registers fixtures (`mock_table`, etc.). |
| 3 | Pytest sees `mock_table` in the test’s parameters. | Runs the **`mock_table` fixture**: builds a fake table with safe defaults (`get_item` → empty item, etc.). |
| 4 | Your test function runs. | First line can override `mock_table.get_item.return_value` to simulate “DB returned this row.” |
| 5 | `PostsService(mock_table)` | `PostsService.__init__` stores the mock as `self._table`. |
| 6 | `svc.get_post("p1")` | `PostsService.get_post` in `core/posts/service.py`. |
| 7 | `dynamodb_util.get_item(self._table, {"postId": "p1"})` | Shared helper in `common/dynamodb_util.py`. |
| 8 | `table.get_item(Key=...)` on the mock | No network: the mock returns the dict you configured in step 4. |
| 9 | `get_item` returns `response.get("Item")` | Your service gets a normal Python dict (or `None` if you simulated a miss). |
| 10 | `assert ...` and `mock_table.get_item.assert_called_once_with(...)` | Pytest checks behavior and that the fake was called with the expected key. |

**One-line chain:**  
`pytest` → `mock_table` fixture → `test_get_post_returns_item` → `PostsService.__init__` → `PostsService.get_post` → `dynamodb_util.get_item` → `mock_table.get_item` → assertions.

**Related create flow:** For `test_create_post_sets_post_id_and_metadata`, the chain is similar, but after `create_post` the code sets `postId`, timestamps, and `created_by`, then calls `dynamodb_util.put_item` → `mock_table.put_item` (still all on the mock).

### 5.2 Webservice handler test (mock service + RBAC)

For `test_get_posts_list_returns_200_and_items` in `unit/webservice/test_posts_handler.py`:

1. You run `PYTHONPATH=backend python -m pytest backend/tests -v`.
2. Pytest loads `conftest.py` → `sys.path` includes `backend/`.
3. Pytest imports `test_posts_handler.py`, which adds `backend/webservice/posts` to `sys.path` and imports `runtime.posts`.
4. The test uses fixtures `mock_context` (from `conftest.py`) and `mock_service` (local fixture).
5. `unittest.mock.patch` replaces `role_util.is_user_action_valid` and `runtime.posts.SERVICE` with mocks.
6. The test builds an API Gateway–style dict via `api_event("GET", "/posts")` and calls `posts_lambda_handler(event, mock_context)`.
7. Assertions check `statusCode`, JSON `body`, and that the mock service was used as expected.

---

## 6. Layout reference

```
backend/tests/
  README.md                 # This file
  conftest.py               # Shared fixtures + sys.path guard for backend/
  helpers.py                # BACKEND_ROOT, api_event() (used by webservice tests)
  unit/
    core/                   # Service tests (mock DynamoDB table)
    common/                 # Shared utilities (e.g. error_mapper)
    webservice/             # Lambda handler tests (mock SERVICE + RBAC)
```

---

## 7. Further reading

For patterns, copy-paste examples, and mocking details, see **[docs/TESTING.md](../../docs/TESTING.md)**.
