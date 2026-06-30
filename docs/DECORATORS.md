# Decorators In This Project

This project uses Python decorators for repeated Lambda handler concerns. The goal is to keep handlers focused on route-specific logic while shared behavior stays in one place.

## What Is A Decorator?

A decorator is a function that wraps another function and can run code before or after it.

Simple example:

```python
@some_decorator
def lambda_handler(event, context):
    return {"ok": True}
```

This is equivalent to:

```python
def lambda_handler(event, context):
    return {"ok": True}

lambda_handler = some_decorator(lambda_handler)
```

In our Lambda handlers, decorators are useful for cross-cutting concerns like:

- Scheduled warmup events
- Shared error handling
- RBAC checks
- Authorizer-specific warmup handling

They are **not** used for domain/business logic. Business behavior remains in service classes like `PostsService` and `UsersService`.

---

## Where Decorators Live

Decorators are defined in:

```text
backend/common/lambda_decorators.py
```

This file is packaged into the shared Lambda layer by:

```bash
cd backend
python build.py
```

So every Lambda can import:

```python
from common.lambda_decorators import api_handler, require_rbac, authorizer_handler
```

---

## Decorators We Use

### `@api_handler(LOGGER)`

Used for normal API Gateway Lambdas.

It handles:

- EventBridge warmup events
- Top-level exception logging
- Mapping unexpected exceptions into frontend-safe API error responses

Example:

```python
@api_handler(LOGGER)
def lambda_handler(event, context):
    ...
```

If the event is a scheduled warmup event, the decorator returns:

```json
{"warmed": true}
```

If an unhandled exception escapes the handler, the decorator logs it and returns a structured error response through `simple_api_util.build_error_from_exception()`.

### `@require_rbac(LOGGER)`

Used for API handlers that require role-based access checks.

It handles:

- Calling `role_util.is_user_action_valid(event)`
- Returning `403 FORBIDDEN` when the current user is not allowed to call the route
- Letting the handler run only after RBAC passes

Example:

```python
@api_handler(LOGGER)
@require_rbac(LOGGER)
def lambda_handler(event, context):
    ...
```

Order matters. In this project:

1. `@api_handler` handles warmup and catches unexpected errors.
2. `@require_rbac` checks route permissions.
3. The actual handler runs.

### `@authorizer_handler()`

Used for the custom Lambda authorizer.

It handles:

- EventBridge warmup events for authorizer Lambdas
- Returning an authorizer-compatible warmup policy

Example:

```python
@authorizer_handler()
def lambda_handler(event, context):
    ...
```

The authorizer still performs JWT validation itself. The decorator only handles warmup behavior.

---

## Current Usage

### Posts API

File:

```text
backend/webservice/posts/runtime/posts.py
```

Decorators:

```python
@api_handler(LOGGER)
@require_rbac(LOGGER)
def lambda_handler(event, context):
    ...
```

Why:

- Posts routes are protected by RBAC.
- The handler should not repeat warmup handling and generic exception mapping.

### Users API

File:

```text
backend/webservice/users/runtime/users.py
```

Decorators:

```python
@api_handler(LOGGER)
@require_rbac(LOGGER)
def lambda_handler(event, context):
    ...
```

Why:

- Users routes are protected by RBAC.
- The handler still contains user-specific checks like self-or-admin access.
- Shared warmup/error behavior is centralized.

### Custom Authorizer

File:

```text
backend/webservice/authorizer/runtime/authorizer.py
```

Decorator:

```python
@authorizer_handler()
def lambda_handler(event, context):
    ...
```

Why:

- Authorizer warmup responses are different from API Gateway proxy responses.
- JWT validation stays explicit in the authorizer handler.

### Cognito Login API

File:

```text
backend/webservice/cognito_login/runtime/cognito_login.py
```

Decorator:

```python
@api_handler(LOGGER)
def lambda_handler(event, context):
    ...
```

Why:

- Login does not use RBAC because it is the route that obtains tokens.
- It still benefits from warmup handling and fallback exception mapping.

---

## When To Add A New Decorator

Add a decorator when the same handler-level concern appears in multiple Lambda files.

Good candidates:

- Request warmup handling
- Consistent error mapping
- RBAC/authorization guard
- Request correlation/logging
- Repeated request parsing that is identical across handlers

Avoid decorators when:

- The behavior is only used once
- The behavior is route-specific
- The decorator would hide important business logic
- The function becomes harder to read or test

Rule of thumb: decorators should make the handler easier to scan, not make control flow mysterious.

---

## Testing Decorated Handlers

Decorated handlers are tested like normal handlers.

Current coverage:

```bash
cd backend
pytest tests/unit
```

Important behaviors covered by existing tests:

- Posts/users route behavior
- RBAC-denied responses
- Warmup utility responses
- Error mapper behavior

When adding a decorator, prefer testing:

- The decorator directly if it has branching behavior
- One decorated handler path to confirm integration

---

## Deployment Note

Because decorators live in `backend/common/`, rebuild the shared layer before deploy:

```bash
cd backend
python build.py
cd ../infrastructure
cdk deploy --all
```
