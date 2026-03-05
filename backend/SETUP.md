# Tech Blog Backend – Setup

## Prerequisites

- Python 3.12+
- AWS CLI configured (for deploy)
- CDK CLI (for deploy)

## Why a Lambda Layer?

`common` and `core` are **not** copied into each webservice folder. They are built once into `layer_bundle/` and deployed as a **Lambda Layer**. Every Lambda has the layer attached, so they all see the same `common` and `core` at runtime. No duplicate code per function.

## Local development

1. From `backend/`, build the layer (creates `layer_bundle/python/{common,core}`):

   ```bash
   python build.py
   ```

2. To run a handler locally, set `PYTHONPATH` so Python can find `common` and `core`, e.g.:

   ```bash
   export PYTHONPATH="backend/layer_bundle/python:backend/webservice/posts_get"
   python -c "from runtime.posts_get import lambda_handler; ..."
   ```

   Or point `PYTHONPATH` at `backend/common` and `backend/core` (and ensure `backend/webservice/<name>` is on the path for the handler).

## Deploy

1. From `backend/`, build the layer:

   ```bash
   python build.py
   ```

2. From `infrastructure/`, deploy. The stack attaches the shared layer to each Lambda; each function’s asset is only `webservice/<name>/` (handler code).

   ```bash
   cdk deploy
   ```

Each Lambda’s `handler` is `runtime.<name>.lambda_handler` (e.g. `runtime.posts_get.lambda_handler`).

## Config

- **config.json** – Per-Lambda settings (timeout, memory, reserved concurrency). Used by your CDK/infra when creating the functions.
