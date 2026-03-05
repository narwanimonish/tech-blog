# Tech Blog Backend – Setup

## Prerequisites

- Python 3.12+
- AWS CLI configured (for deploy)
- CDK CLI (for deploy)

## Local development

1. From `backend/` run the build so each Lambda package has `common` and `core`:

   ```bash
   python build.py
   ```

2. Each Lambda entrypoint is under `webservice/<name>/runtime/<name>.py` with handler `lambda_handler`. To run a handler locally, set `PYTHONPATH` to the built package directory (e.g. `webservice/posts_get`) and invoke the handler with a test event.

## Deploy

1. From `backend/`, run:

   ```bash
   python build.py
   ```

2. From `infrastructure/`, point CDK at the built Lambda folders (e.g. `../backend/webservice/posts_get`) and deploy:

   ```bash
   cdk deploy
   ```

Ensure each Lambda’s `handler` is set to `runtime.<name>.lambda_handler` (e.g. `runtime.posts_get.lambda_handler`).

## Config

- **config.json** – Per-Lambda settings (timeout, memory, reserved concurrency). Consumed by your deployment/infra (e.g. CDK) when creating the functions.
