# Backend tests

Unit tests for core services, Lambda handlers, and common modules (e.g. error_mapper).

**Run (from repo root):**

```bash
pip install -r infrastructure/requirements-dev.txt
PYTHONPATH=backend python -m pytest backend/tests -v
```

See **docs/TESTING.md** for how to write tests for API handlers and core logic (mocking strategy, fixtures, and examples).
