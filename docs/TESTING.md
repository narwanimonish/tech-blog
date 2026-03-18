# How to write and run unit tests for API handlers and core services

This guide explains how we test Lambda handlers and core service logic without calling real AWS services.

---

## 1. Test layout

```
backend/
  tests/
    conftest.py          # Shared fixtures: mock_table, mock_context, base_event, api_event()
    helpers.py           # BACKEND_ROOT, api_event() for building API Gateway events
    unit/
      core/              # Service-layer tests (mock DynamoDB table)
        test_users_service.py
        test_posts_service.py
      common/            # Common module tests (e.g. error_mapper)
        test_error_mapper.py
      webservice/        # Handler tests (mock SERVICE and role_util)
        test_users_handler.py
        test_posts_handler.py
```

- **Core tests** – Use a **mocked DynamoDB table** (`MagicMock`). The real `UsersService` / `PostsService` runs against this mock, so you assert on return values and that `get_item` / `put_item` / `scan` / `delete_item` were called with the right keys/items.
- **Handler tests** – Use **mocked `SERVICE` and `role_util.is_user_action_valid`**. The real handler code runs, but it calls the mock service and the mock RBAC check. You assert on HTTP status, response body (e.g. `items`, `errorCode`), and that the service was called with the expected arguments.

---

## 2. Running tests

**Prerequisites:** Python 3.11+, pytest, boto3 (for handler imports and error_mapper’s `ClientError`).

```bash
# From repo root (recommended)
pip install -r infrastructure/requirements-dev.txt
PYTHONPATH=backend python -m pytest backend/tests -v

# From backend directory
cd backend
pip install -r ../infrastructure/requirements-dev.txt
PYTHONPATH=. python -m pytest tests -v
```

- `PYTHONPATH=backend` (or `PYTHONPATH=.` from `backend/`) is required so that `from common import ...` and `from core import ...` resolve to `backend/common` and `backend/core`.
- Handler tests add `backend/webservice/<users|posts>` to `sys.path` so that `from runtime.users import lambda_handler` (or `runtime.posts`) loads the correct module.

---

## 3. Testing core services (e.g. `UsersService`, `PostsService`)

**Idea:** Pass a **mock table** into the service constructor. Configure the mock’s return values (e.g. `get_item.return_value = {"Item": {...}}`), call the service method, then assert on the return value and that the table was called correctly.

**Fixture:** `mock_table` in `conftest.py` – a `MagicMock` with `get_item`, `put_item`, `delete_item`, `scan` (and `scan`’s `LastEvaluatedKey` for pagination).

**Example (users):**

```python
def test_get_user_returns_item(mock_table):
    mock_table.get_item.return_value = {"Item": {"userId": "u1", "email": "a@b.com", "name": "Alice"}}
    svc = UsersService(mock_table)
    result = svc.get_user("u1")
    assert result == {"userId": "u1", "email": "a@b.com", "name": "Alice"}
    mock_table.get_item.assert_called_once_with(Key={"userId": "u1"})
```

**Example (posts – creation_time / created_by):**

```python
def test_create_post_sets_post_id_and_metadata(mock_table):
    svc = PostsService(mock_table)
    result = svc.create_post({"title": "Hi", "body": "World"}, created_by="author@example.com")
    assert "postId" in result
    assert result["created_by"] == "author@example.com"
    assert "creation_time" in result
    mock_table.put_item.assert_called_once()
    call_item = mock_table.put_item.call_args[1]["Item"]
    assert call_item["created_by"] == "author@example.com"
```

**Example (posts – update preserves creation_time / created_by):**

```python
def test_update_post_preserves_creation_time_and_created_by(mock_table):
    mock_table.get_item.return_value = {
        "Item": {"postId": "p1", "creation_time": "2025-01-01T00:00:00Z", "created_by": "original@example.com"}
    }
    svc = PostsService(mock_table)
    result = svc.update_post("p1", {"title": "New", "body": "New"})
    call_item = mock_table.put_item.call_args[1]["Item"]
    assert call_item["creation_time"] == "2025-01-01T00:00:00Z"
    assert call_item["created_by"] == "original@example.com"
```

---

## 4. Testing Lambda handlers (API behaviour)

**Idea:** Build an API Gateway proxy **event** and a minimal **context**, then call `lambda_handler(event, context)`. Mock **RBAC** and the **service** so that no real DynamoDB or role lookup runs. Assert on `statusCode`, parsed `body` (e.g. `items`, `errorCode`, `message`, `requestId`), and that the mock service was called with the right arguments.

**Fixtures:**

- `mock_context` – provides `aws_request_id` (e.g. for `requestId` in error responses).
- `api_event(method, path, path_params=None, body=None, authorizer=None)` – builds an event with `httpMethod`, `path`, `requestContext.authorizer`, `pathParameters`, `body` (JSON string if `body` is a dict).

**Patches:**

- `runtime.users.role_util.is_user_action_valid` (or `runtime.posts.role_util.is_user_action_valid`) → `return_value=(True, "")` for “allowed” or `(False, "message")` for 403.
- `runtime.users.SERVICE` (or `runtime.posts.SERVICE`) → a `MagicMock()`; set e.g. `mock_service.list_users.return_value = [...]`, `mock_service.get_user.return_value = None` for 404, etc.

**Example – GET list returns 200 and items:**

```python
def test_get_users_list_returns_200_and_items(mock_context, mock_service):
    mock_service.list_users.return_value = [{"userId": "u1", "email": "a@b.com"}]
    event = api_event("GET", "/users")
    with patch("runtime.users.role_util.is_user_action_valid", return_value=(True, "")):
        with patch("runtime.users.SERVICE", mock_service):
            resp = users_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "items" in body
    assert body["items"][0]["userId"] == "u1"
```

**Example – RBAC denied returns 403:**

```python
def test_rbac_denied_returns_403(mock_context, mock_service):
    event = api_event("GET", "/users")
    with patch("runtime.users.role_util.is_user_action_valid", return_value=(False, "Insufficient permission")):
        with patch("runtime.users.SERVICE", mock_service):
            resp = users_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 403
    body = json.loads(resp["body"])
    assert body.get("errorCode") == "FORBIDDEN"
    assert "requestId" in body
```

**Example – PUT with missing body returns 400:**

```python
def test_put_user_returns_400_when_body_missing(mock_context, mock_service):
    event = api_event("PUT", "/users/u1", path_params={"userId": "u1"}, body=None)
    event["body"] = None
    event["path"] = "/users/u1"
    with patch("runtime.users.role_util.is_user_action_valid", return_value=(True, "")):
        with patch("runtime.users.SERVICE", mock_service):
            resp = users_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 400
    assert json.loads(resp["body"]).get("errorCode") == "BAD_REQUEST"
```

**Importing the handler:** Handler code lives under `backend/webservice/<users|posts>/runtime/<name>.py`. To keep “runtime” importable, each handler test file inserts `backend/webservice/<users|posts>` into `sys.path`, then does `from runtime.users import lambda_handler` (or `runtime.posts`). That way the same handler code as in Lambda runs, with only `SERVICE` and `role_util` replaced by mocks.

---

## 5. Testing the error mapper

`common.error_mapper` has no AWS or handler dependencies; only `botocore.exceptions.ClientError` is used for AWS error mapping. So you need `botocore` (or `boto3`, which pulls it in) installed to run these tests.

**Example:**

```python
from common.error_mapper import map_exception
from common.errors import AppError

def test_app_error_maps_to_frontend_error():
    exc = AppError("VALIDATION_FAILED", "Invalid field", status_code=400)
    result = map_exception(exc)
    assert result.code == "VALIDATION_FAILED"
    assert result.status_code == 400

def test_client_error_resource_not_found_maps_to_not_found():
    resp = {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}}
    exc = ClientError(resp, "GetItem")
    result = map_exception(exc)
    assert result.code == "NOT_FOUND"
    assert result.status_code == 404
```

---

## 6. Summary

| What you want to test | Mock | Assert on |
|------------------------|------|-----------|
| **Service method** (e.g. `create_post`, `update_post`) | DynamoDB table (`mock_table`) | Return value; `put_item` / `get_item` / `scan` / `delete_item` call args |
| **Handler response** (status, body, error shape) | `SERVICE`, `role_util.is_user_action_valid` | `statusCode`, `body` (parsed), `errorCode` / `requestId` where relevant; service call args |
| **Error mapper** | Nothing (real exceptions) | `FrontendError.code`, `status_code`, `message` |

Install dev deps (`pytest`, `boto3`), set `PYTHONPATH=backend`, and run `pytest backend/tests -v`. Add new tests in the same structure (core → `unit/core`, handlers → `unit/webservice`, common → `unit/common`).
