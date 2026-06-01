# Postman API testing

Smoke and performance tests for **every** Tech Blog API endpoint (`backend/api-spec.yaml`) using a Postman collection and [Newman](https://github.com/postmanlabs/newman).

## Layout

```
postman/
  collections/tech-blog-api.postman_collection.json   # generated — see scripts/
  scripts/generate-collection.py
  environments/template.postman_environment.json
  environments/local.postman_environment.json.example
  reports/
  package.json
scripts/postman-run.sh
scripts/postman-ci.sh
```

Regenerate the collection after editing `generate-collection.py`:

```bash
python3 postman/scripts/generate-collection.py
```

## Credentials

Use an **admin** Cognito user for full pipeline coverage (`POSTMAN_USERNAME` / `POSTMAN_PASSWORD`). Admin is required for:

- `GET /users`
- `PUT /users/{userId}/role`
- Optional `DELETE /users/{userId}` (see below)

Writer/reader accounts will fail on user-admin steps.

## Quick start

1. **Install Node.js** (18+).

2. **Create a local environment** (not committed):

   ```bash
   cp postman/environments/local.postman_environment.json.example \
      postman/environments/local.postman_environment.json
   ```

   Edit `username` and `password` (admin). Leave `baseUrl` empty to auto-resolve from `TechBlogApiStack` when AWS credentials are valid.

3. **Run smoke** (one pass, all APIs):

   ```bash
   make postman-smoke
   ```

4. **Run performance** (repeat full API flow):

   ```bash
   make postman-perf
   PERF_ITERATIONS=50 PERF_DELAY_MS=50 make postman-perf
   ```

   | Variable | Default | Meaning |
   |----------|---------|---------|
   | `PERF_ITERATIONS` | `20` | Newman loop count |
   | `PERF_DELAY_MS` | `100` | Pause between requests (ms) |
   | `MAX_RESPONSE_MS` | `3000` | Fail if any request exceeds this (ms) |

## Endpoints exercised (Smoke & Performance)

| # | Method | Path | Notes |
|---|--------|------|-------|
| 1 | POST | `/auth/login` | Public |
| 2 | GET | `/users` | Admin |
| 3 | GET | `/users/{userId}` | Own profile |
| 4 | PUT | `/users/{userId}` | Idempotent profile update |
| 5 | PUT | `/users/{userId}/role` | Sets same role (no-op) |
| 6 | GET | `/posts` | |
| 7 | POST | `/posts` | Creates temp post |
| 8 | GET | `/posts/{postId}` | |
| 9 | PUT | `/posts/{postId}` | |
| 10 | DELETE | `/posts/{postId}` | Cleans up temp post |
| 11 | DELETE | `/users/{userId}` | **Skipped** unless `disposableUserId` is set |

Optional: set `POSTMAN_DISPOSABLE_USER_ID` (CI) or `disposableUserId` (local env) to a **throwaway** user UUID to enable step 11. Never point this at your admin account.

## CI / GitHub Actions

After deploy, [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml) runs `scripts/postman-ci.sh pipeline`:

1. **Smoke** — folder `Smoke` (all APIs once)
2. **Performance** — folder `Performance - All APIs` (default **10** iterations)

Add environment secrets on `development` and `production`:

| Secret | Value |
|--------|--------|
| `POSTMAN_USERNAME` | Admin Cognito email |
| `POSTMAN_PASSWORD` | Admin password |

Optional: `POSTMAN_DISPOSABLE_USER_ID` for DELETE user perf step.

Heavy manual runs: workflow **Postman performance (manual)**.

## Makefile

```bash
make postman-install
make postman-smoke
make postman-perf
make postman-pipeline   # smoke + perf (like CI)
```

## Related docs

- `backend/README.md` — sample requests
- `backend/api-spec.yaml` — OpenAPI
- `docs/CI_CD.md` — pipeline secrets setup
