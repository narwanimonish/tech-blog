# TaskMaster-style architecture (target) — tech-blog alignment

This document defines **standards and a roadmap** inspired by a multi-module serverless “TaskMaster” layout: contract-first API, clear model boundaries, IaC, fast tooling, and layered security. **Tech-blog today** differs; use the mapping below to evolve incrementally without a big-bang rewrite.

---

## 1. Core principles

| Principle | TaskMaster-style target | Tech-blog today | Evolution |
|-----------|-------------------------|-----------------|-----------|
| **Contract-first** | `openapi.yaml` is SSOT; codegen DTOs | `backend/api-spec.yaml` | Keep spec as SSOT; add `make generate` when you adopt datamodel-codegen or openapi-generator |
| **Triple model isolation** | API DTOs (generated) → Domain entities → DB models (aliases, single-table) | Handlers parse dicts; `core` services + Dynamo items as dicts | Introduce thin DTO layer per route or Pydantic models in handlers first; domain classes optional |
| **IaC** | CDK Python, modular stacks | `infrastructure/` + `TechBlog*` stacks | Already aligned; add SSM for cross-stack refs when you split services |
| **Package mgmt** | UV workspace + lock | pip + `requirements*.txt` | Optional: UV workspace at repo root; keep Lambda assets on pinned deps |
| **Zero-trust** | Authorizer + `@has_permission` / decorator | Custom authorizer + `role_util.is_user_action_valid` | Add decorator wrapper around handlers if you want parity with “decorator at edge of logic” |

---

## 2. Target repository structure (reference)

Use this as a **north star** when splitting modules or starting a greenfield sibling repo.

```text
/taskmaster-root
├── openapi.yaml                 # Shared API contract (SSOT)
├── Makefile                     # sync | generate | test | cdk-synth | deploy-*
├── pyproject.toml               # UV workspace + tools (optional)
├── common/                      # Shared library → Lambda layer
│   └── python/common/
│       ├── generated/           # Pydantic from OpenAPI (optional)
│       ├── decorators.py        # @api_gateway_handler, @has_permission
│       ├── auth.py              # RBAC resolver (DB or config)
│       ├── observability.py     # Powertools (optional)
│       └── exceptions.py        # Domain / HTTP exceptions
├── services/
│   ├── tasks-api/               # Handlers, services, repos per domain
│   └── admin-api/
├── ui/                          # Frontend + generated TS types
└── infra/
    ├── app.py
    └── stacks/
```

### Map to **tech-blog** (current)

```text
tech-blog/
├── backend/api-spec.yaml        # ≈ openapi.yaml (rename optional)
├── Makefile                     # thin targets (see repo root)
├── pyproject.toml               # Ruff today; UV optional later
├── backend/common/              # ≈ common/python/common (Lambda layer)
│   ├── role_util.py, error_mapper.py, …  # ≈ auth + errors split
│   └── rbac_config/*.json       # static RBAC (TaskMaster might use RBAC_TABLE)
├── backend/core/                # ≈ domain services
├── backend/webservice/          # ≈ services/*/ handlers (per Lambda asset)
├── infrastructure/              # ≈ infra/
└── (no ui/ in repo)             # add ui/ if you add a frontend
```

---

## 3. Security & RBAC (TaskMaster vs tech-blog)

| Aspect | TaskMaster-style | Tech-blog |
|--------|------------------|-----------|
| Identity | Cognito JWT + **groups** | Cognito JWT; **role** on user row in DynamoDB |
| Edge | Authorizer loads **RBAC_TABLE** by group | Authorizer validates token; **RBAC** in JSON + `is_user_action_valid` |
| Handler | `@has_permission("tasks:write")` | Explicit call to `role_util.is_user_action_valid(event)` |

**Roadmap:** keep JSON RBAC until you need runtime edits; then mirror the pattern with a small **permissions** table and resolver in `common/auth.py`.

---

## 4. Shared layer standards (parity checklist)

- **Decorator `api_gateway_handler`:** try/except → single `map_error_to_response` (tech-blog: `build_error_from_exception` in handlers — optional wrapper).
- **Error map:** exception type → HTTP status + `errorCode` (tech-blog: `error_mapper.py` + `AppError`).
- **Observability:** AWS Lambda Powertools logger/tracer (optional add-on).

---

## 5. Persistence (single-table design)

TaskMaster uses **aliased Pydantic DB models** (`PK`, `SK`, short attribute names). Tech-blog uses **separate tables** (`userId`, `postId`) and plain dicts. Moving to single-table is a **data migration** project; until then, keep explicit table services and optional Pydantic **input** validation only.

---

## 6. Infrastructure (CDK)

- **TaskMaster:** SSM Parameter Store to wire stacks. **Tech-blog:** stack outputs + env vars; add SSM when cross-stack coupling grows.
- **Scoped IAM:** already pattern `grant_read_write_data` on table constructs — keep as standard.

---

## 7. Build & test (Makefile targets)

Repo root **Makefile** provides names familiar to TaskMaster users:

| Target | Intent |
|--------|--------|
| `make test` | Run backend pytest from repo root |
| `make lint` | Ruff check + format check on `backend/` |
| `make generate` | Placeholder: wire OpenAPI → Python/TS when you add codegen |
| `make cdk-synth` | CDK synth from `infrastructure/` (requires venv + AWS env) |

---

## 8. Implementation roadmap (phased)

1. **Contract:** Keep `api-spec.yaml` authoritative; any new route updates spec first.
2. **Environment:** Optional UV at root; until then `pip install -r infrastructure/requirements-dev.txt`.
3. **Core infra:** Already: Cognito, DynamoDB, API + authorizer (tech-blog stacks).
4. **RBAC:** JSON today; optional **RBAC_TABLE** + seed Lambda later.
5. **Service dev:** Handler → service → `dynamodb_util`; add repository layer only when complexity warrants.
6. **UI:** Add `ui/` + generated clients when frontend lands.
7. **Validation:** Expand pytest; add Schemathesis or contract tests against spec when API stabilizes.

---

## 9. Agent / onboarding pointers

- Cursor rule: `.cursor/rules/backend-lambda-playbook.mdc`
- Prompts: `docs/BACKEND_PLAYBOOK_PROMPTS.md`
- This doc: **target shape** vs **current tree** — agents should prefer small steps that move toward the target without breaking deploys.
