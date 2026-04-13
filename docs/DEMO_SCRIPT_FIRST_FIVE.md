# Demo script – first five topics (≈25–35 minutes)

Use this when walking the team through **project structure**, **Lambda layers**, **Cognito + authorizer**, **RBAC**, and **unit tests**. Adjust depth to your audience.

**Before the demo**

- Repo open in the IDE; terminal at repo root.
- Optional: `pip install -r infrastructure/requirements-dev.txt` and verify  
  `PYTHONPATH=backend python -m pytest backend/tests -q` passes.
- Optional: run `cd backend && python build.py` once so `layer_bundle/` exists for §2.

---

## Opening (1 minute)

**Say:**  
“Today I’ll walk through how the backend is organized, how we ship shared code on a Lambda layer, how Cognito and the API authorizer fit in, how role-based access works after you’re authenticated, and how we test the core logic without hitting AWS.”

**Show:**  
`docs/PROJECT_OUTLINE.md` sections 1–5 as the agenda (optional).

---

## 1. Project code structure (5–7 minutes)

**Say:**  
“We split the backend into three layers. **Common** is shared utilities and RBAC config. **Core** is domain logic—posts and users services that talk to DynamoDB through small helpers. **Webservice** is only Lambda entrypoints: thin handlers that parse the API Gateway event, check permissions, and call core. The **OpenAPI spec** is the contract for the HTTP API. **Infrastructure** is CDK—separate from runtime Python.”

**Show (IDE, top to bottom):**

1. `backend/common/` — open `dynamodb_util.py` or `role_util.py` (one glance).
2. `backend/core/posts/service.py` — “business rules live here.”
3. `backend/webservice/posts/runtime/posts.py` — “handler stays thin; imports from common/core via the layer in AWS.”
4. `backend/api-spec.yaml` — collapse to show paths (users, posts, auth).
5. `infrastructure/app.py` — “four stacks wired in order: data → auth → lambdas → API.”

**Closing line:**  
“So: **common + core** = reusable brain; **webservice** = one zip per function; **infra** = how it lands in AWS.”

---

## 2. Lambda layers and common code deployment (4–6 minutes)

**Say:**  
“We don’t copy `common` and `core` into every Lambda zip. We build one **layer** artifact and attach it to each function. That keeps deploys smaller and guarantees every function runs the same shared code and RBAC JSON.”

**Show:**

1. `backend/build.py` — read the docstring at the top (purpose in one screen).
2. Run (if not already built):

   ```bash
   cd backend && python build.py
   ```

3. Show `backend/layer_bundle/python/common/` and `layer_bundle/python/core/` in the file tree.
4. Open `infrastructure/stacks/tech_blog_lambda_stack.py` — point to **`SharedLayer`** and that **`users_api` / `posts_api`** use the same layer.

**Closing line:**  
“Handlers in `webservice/*/runtime/` are the only thing unique per function; shared code rides on the layer.”

---

## 3. Cognito auth and Lambda authorizer (5–7 minutes)

**Say:**  
“Users sign up and sign in with **Cognito**. The User Pool issues JWTs. Our **API Gateway** uses a **custom Lambda authorizer**: it validates the token before the request reaches the users or posts Lambdas. If the token is bad, API Gateway returns 401/403 and the business Lambdas never run. If it’s good, we get the user identity—like **`sub`**—in the event for downstream code.”

**Show:**

1. `infrastructure/stacks/tech_blog_auth_stack.py` — “pool, client, triggers” (high level).
2. `infrastructure/stacks/tech_blog_api_stack.py` — find the **authorizer** Lambda construct; mention it lives in the API stack to avoid circular dependencies with the Lambda stack.
3. Optionally open `backend/webservice/authorizer/` — “this is the code that validates the JWT.”
4. Mention **Cognito trigger** folders under `backend/webservice/` — “these sync users into DynamoDB and set defaults.”

**Closing line:**  
“Authorizer answers: *is this JWT valid?* It does **not** answer: *is this user allowed to delete that user?* That’s RBAC next.”

---

## 4. RBAC (5–8 minutes)

**Say:**  
“After the token is valid, we still check **role-based access**: admin vs writer vs reader. The user’s **role** is stored in the **users** DynamoDB table. Required permissions for each **path and HTTP method** live in JSON. One function, **`is_user_action_valid`**, loads the role, expands permissions using dependency rules in config, and returns allow or deny. Deny is always **403** with our standard error shape.”

**Show:**

1. `backend/common/rbac_config/` — open briefly:
   - `consolidated_api_permissions.json` — find one line, e.g. `GET /posts` vs `POST /posts`.
   - `role_permissions.json` — show admin / writer / reader.
2. `backend/common/role_util.py` — scroll to **`is_user_action_valid`** (signature + docstring).
3. `backend/webservice/posts/runtime/posts.py` — show the early call to **`role_util.is_user_action_valid`** (first lines after imports).

**Optional diagram (whiteboard or speech):**  
`Request → API GW → Authorizer (JWT) → Handler → RBAC (role + path) → Service → DynamoDB`

**Closing line:**  
“Changing who can do what is mostly **config**, not a redeploy of business logic—unless we add new APIs.”

---

## 5. Unit testing (4–6 minutes)

**Say:**  
“We use **pytest**. **Core** tests mock DynamoDB with a fake table so we never call AWS. **Handler** tests mock the **service** and RBAC so we exercise HTTP parsing and status codes without deploying. CI sets a dummy **AWS region** because importing handlers touches `boto3` at module load—even though tests don’t hit the network.”

**Show:**

1. `backend/tests/conftest.py` — **`mock_table`** fixture.
2. `backend/tests/unit/core/test_posts_service.py` — one test, e.g. **`test_get_post_returns_item`**.
3. `backend/tests/unit/webservice/test_posts_handler.py` — mention **`patch`** for `SERVICE` and RBAC.

**Run live:**

```bash
cd /path/to/tech-blog
export AWS_DEFAULT_REGION=us-east-1   # if your machine has no AWS config
PYTHONPATH=backend python -m pytest backend/tests -v
```

**Closing line:**  
“Fast feedback on services and handlers; integration against real API is a separate step if we add it later.”

---

## Wrap-up (1–2 minutes)

**Say:**  
“Recap: **structure** separates common, core, and handlers; **layers** deploy shared code once; **Cognito + authorizer** authenticate; **RBAC** authorizes per route; **pytest** protects behavior without AWS. Questions?”

**Optional follow-ups for the team**

- Where to change Lambda memory/timeout: `backend/config.json` + CDK.
- Full RBAC narrative: `docs/IMPLEMENTATION.md` section 2.
- How to run tests locally: `backend/tests/README.md`.
