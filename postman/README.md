# Postman API testing

Smoke and performance tests for the deployed Tech Blog API using a Postman collection and [Newman](https://github.com/postmanlabs/newman) (CLI runner).

## Layout

```
postman/
  collections/tech-blog-api.postman_collection.json
  environments/template.postman_environment.json   # placeholders (safe to commit)
  environments/local.postman_environment.json.example
  reports/                                       # Newman JSON reports (gitignored)
  package.json
scripts/postman-run.sh
```

## Quick start

1. **Install Node.js** (18+).

2. **Create a local environment** (not committed):

   ```bash
   cp postman/environments/local.postman_environment.json.example \
      postman/environments/local.postman_environment.json
   ```

   Edit `baseUrl`, `username`, and `password`. Leave `baseUrl` empty to auto-resolve from `TechBlogApiStack` when AWS credentials are valid.

3. **Optional — resolve API URL from AWS:**

   ```bash
   RESOLVE_API_URL_FROM_AWS=1 bash scripts/postman-run.sh smoke
   ```

4. **Run smoke test** (single pass: login → list posts → get post):

   ```bash
   make postman-smoke
   # or
   bash scripts/postman-run.sh smoke
   ```

5. **Run performance test** (repeat read-only flow with timing assertions):

   ```bash
   make postman-perf
   # or
   PERF_ITERATIONS=50 PERF_DELAY_MS=50 bash scripts/postman-run.sh perf
   ```

   Tune with:

   | Variable | Default | Meaning |
   |----------|---------|---------|
   | `PERF_ITERATIONS` | `20` | How many times Newman runs the folder |
   | `PERF_DELAY_MS` | `100` | Pause between requests (ms) |
   | `MAX_RESPONSE_MS` | `3000` | Fail if any request exceeds this (ms) |

   JSON report is written under `postman/reports/perf-*.json`.

## Postman desktop (GUI)

1. **Import** `postman/collections/tech-blog-api.postman_collection.json`.
2. **Import** your `local.postman_environment.json` and select it.
3. **Functional smoke:** open folder **Smoke** → **Run** → Run collection (1 iteration).
4. **Performance testing (Postman app):**
   - Open the collection → **Run** → select folder **Performance - Read APIs**.
   - Switch to the **Performance** tab (Postman v10+).
   - Set virtual users, duration, and ramp profile.
   - Start the run and review latency percentiles in the Postman performance report.

   The same folder is used by Newman; GUI performance adds concurrent virtual users and richer charts.

## Collection folders

| Folder | Purpose |
|--------|---------|
| **Auth** | Login; sets `accessToken` |
| **Users** / **Posts** | Manual CRUD exploration |
| **Smoke** | CI-friendly single pass |
| **Performance - Read APIs** | Login + GET posts + GET post; asserts status and `maxResponseMs` |

Performance folder is **read-only** so repeated runs do not create or delete data.

## Makefile targets

```bash
make postman-install   # npm install in postman/
make postman-smoke     # functional smoke
make postman-perf      # Newman performance loop (20 iterations)
```

## CI / GitHub Actions

Postman runs automatically **after deploy** in [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml):

- **Smoke** — Newman folder `Smoke`
- **Performance** — folder `Performance - Read APIs` (default **10** iterations on push; configurable on manual deploy)

Add GitHub environment secrets **`POSTMAN_USERNAME`** and **`POSTMAN_PASSWORD`** to `development` and `production`. The pipeline resolves `baseUrl` from `TechBlogApiStack`.

Heavy manual runs: workflow **Postman performance (manual)** (default 50 iterations).

Local CI parity:

```bash
POSTMAN_USERNAME=you@example.com POSTMAN_PASSWORD='...' bash scripts/postman-ci.sh pipeline
```

## Related docs

- Sample requests and env vars: `backend/README.md` (Postman API Guide)
- OpenAPI: `backend/api-spec.yaml`
- API health check: `make cdk-diagnose-api`
