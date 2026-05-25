# Backend playbook – Cursor prompts & agent setup

Reusable copy-paste prompts and Cursor configuration to speed up Lambda/API work. Pair with your own “Implementation Playbook” checklist (testing, errors, RBAC, OpenAPI, CI).

**TaskMaster-style repo layout (contract-first, `services/`, UV, decorators, Makefile):** see **[TASKMASTER_STYLE_ARCHITECTURE.md](TASKMASTER_STYLE_ARCHITECTURE.md)** for a target tree mapped to this repo and a phased roadmap.

---

## 1. Cursor rule (already in this repo)

- **File:** `.cursor/rules/backend-lambda-playbook.mdc`  
- **Behavior:** Applies when editing `backend/**/*.py`, `infrastructure/**/*.py`, or `backend/api-spec.yaml`.  
- **New project:** Copy `.cursor/rules/backend-lambda-playbook.mdc` into the new repo (keep or adjust `globs`).

**Optional – always-on for a backend-only repo:** set `alwaysApply: true` and remove `globs` in that file.

---

## 2. Suggested User rules (Cursor → Settings → Rules)

Add short global instructions the agent always sees:

- Follow the backend playbook: thin handlers, services for logic, shared errors and RBAC; update OpenAPI and tests with every route change.
- Run tests from **repository root**; use `PYTHONPATH` as documented in `backend/tests/README.md` (or your project’s equivalent).
- Do not log access tokens or passwords; redact PII in logs.
- Prefer least-privilege IAM; no drive-by refactors outside the requested scope.

---

## 3. Copy-paste prompts

Replace `{placeholders}` with your domain (e.g. orders, invoices, admin/operator/viewer).

### 3.1 New project / repo bootstrap

```text
I'm starting a Python Lambda + API Gateway backend. Align with our playbook:
- Layout: thin handlers → services → common (DB helpers, error_mapper, AppError, response helpers).
- OpenAPI as source of truth; pytest for services and handlers (mock DB and RBAC).
- Optional RBAC: three JSON files (service levels, API path+method → permissions, role → service.level) and is_user_action_valid(event) at the start of each protected handler; 403 FORBIDDEN with errorCode, message, requestId.
- CDK (or chosen IaC): Lambda layer for shared code, per-function env and IAM to specific resources, config file for timeout/memory/concurrency.
- GitHub Actions (or similar): ruff/pytest on PR.

Scaffold: {list folders/files you want}. Domain services: {e.g. orders, customers}. Roles: {e.g. admin, operator, viewer}.
```

### 3.2 New REST endpoint (full vertical slice)

```text
Add {METHOD} {/path/with/{param}} for {short description}.

Requirements:
- OpenAPI: path, method, request/response schemas, security, error responses.
- Handler: validate body/path, call is_user_action_valid if RBAC exists, call service, return build_response / build_error_* only.
- Service method on {ServiceName}; use dynamodb_util (or project DB helper).
- consolidated_api_permissions: path template + method + required permissions list.
- pytest: service test with mock table; handler test with patched service and RBAC.
- CDK: API Gateway route + Lambda env if new table/stream needed; IAM least privilege.
Do not change unrelated routes or refactors outside this slice.
```

### 3.3 RBAC only (new permission row)

```text
Add RBAC for {METHOD} {/path/template} requiring permission(s) {service.level, ...}.

Update consolidated_api_permissions.json (path must match normalized template, e.g. /users/{userId}/role). Ensure role_util path normalization covers API Gateway: resource, resourcePath, stage prefix /dev/, and httpMethod from event or requestContext. Add or adjust unit tests for path matching.
```

### 3.4 Error handling / new error code

```text
Introduce handling for {scenario} with HTTP {status} and errorCode {CODE}. Use AppError or extend error_mapper; ensure build_error_from_exception maps it. Update OpenAPI error example if public. Add a small unit test in test_error_mapper (or equivalent).
```

### 3.5 Tests only

```text
Add pytest coverage for {module or handler}: {list behaviors}. Use existing fixtures (e.g. mock_table); mock RBAC and service in handler tests. Run from repo root with the project’s documented PYTHONPATH and pytest path.
```

### 3.6 Infra / CDK only

```text
Update CDK for {stack}: {change}. Preserve existing patterns (Lambda layer asset path, config.json for Lambda settings). Grant only required IAM actions on specific ARNs. Output any new env vars the Lambda needs.
```

### 3.7 Pre-release review (agent as reviewer)

```text
Review this backend against our playbook (Section 1 checklist). For each area (testing, errors, config, structure, validation, security, docs, CI), mark Not yet / Partial / Done with evidence (file paths). List the top 5 gaps and concrete fixes—no large refactors unless critical.
```

### 3.8 Onboarding snippet for new joiners

```text
Summarize how this repo implements: (1) request flow from API Gateway to handler to service, (2) error response shape and where it’s built, (3) RBAC files and is_user_action_valid, (4) where OpenAPI lives and how to run tests. Use file paths and one sequence diagram in mermaid if helpful.
```

---

## 4. Agent / Composer usage tips

| Goal | Tip |
|------|-----|
| **Stay on scope** | Start prompts with “Only touch {files/areas}” and end with “Do not refactor unrelated code.” |
| **Faster reviews** | @-mention `api-spec.yaml`, handler, service, `consolidated_api_permissions.json`, and test file in one message. |
| **Fewer path bugs** | Mention “repo root” when asking the agent to run terminal commands. |
| **Consistent RBAC** | Paste a one-line example of your path template + method + permissions JSON shape. |

---

## 5. Optional: `AGENTS.md` (repo root)

For any repo using Cursor or other agents, a one-liner at the top of `AGENTS.md` helps:

```markdown
# Agent notes
- Backend conventions: see `.cursor/rules/backend-lambda-playbook.mdc` and `docs/BACKEND_PLAYBOOK_PROMPTS.md`.
- Tests: run from monorepo root (see `backend/tests/README.md`).
```

---

*Adapt section titles and file paths if your layout differs from `backend/` + `infrastructure/`.*
