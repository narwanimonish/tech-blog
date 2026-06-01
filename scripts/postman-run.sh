#!/usr/bin/env bash
# Run Postman collections via Newman (smoke or performance).
# Requires Node.js. Configure credentials in postman/environments/local.postman_environment.json
#
# Usage (from repo root):
#   bash scripts/postman-run.sh smoke
#   bash scripts/postman-run.sh perf
#   RESOLVE_API_URL_FROM_AWS=1 bash scripts/postman-run.sh smoke
#
# If local baseUrl is still the template placeholder, the script tries AWS automatically
# (when credentials work). Set RESOLVE_API_URL_FROM_AWS=0 to disable auto-resolve.
#
# Environment overrides:
#   POSTMAN_ENV_FILE   path to Postman environment JSON (default: local or template)
#   PERF_ITERATIONS    performance loop count (default: 20)
#   PERF_DELAY_MS      delay between requests in ms (default: 100)
#   MAX_RESPONSE_MS    written into env for response-time assertions (default: 3000)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
POSTMAN_DIR="$ROOT/postman"
COLLECTION="$POSTMAN_DIR/collections/tech-blog-api.postman_collection.json"
MODE="${1:-smoke}"

if [[ ! -f "$COLLECTION" ]]; then
  echo "Collection not found: $COLLECTION" >&2
  exit 1
fi

if [[ -n "${POSTMAN_ENV_FILE:-}" ]]; then
  ENV_FILE="$POSTMAN_ENV_FILE"
elif [[ -f "$POSTMAN_DIR/environments/local.postman_environment.json" ]]; then
  ENV_FILE="$POSTMAN_DIR/environments/local.postman_environment.json"
else
  ENV_FILE="$POSTMAN_DIR/environments/template.postman_environment.json"
  echo "Tip: copy postman/environments/local.postman_environment.json.example to local.postman_environment.json" >&2
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

if [[ "${RESOLVE_API_URL_FROM_AWS:-}" == "1" ]]; then
  API_URL=$(aws cloudformation describe-stacks \
    --stack-name TechBlogApiStack \
    --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
    --output text 2>/dev/null || echo "")
  API_URL="${API_URL%/}"
  if [[ -z "$API_URL" || "$API_URL" == "None" ]]; then
    echo "Could not resolve ApiUrl from TechBlogApiStack (AWS credentials / stack missing?)" >&2
    exit 1
  fi
  export POSTMAN_BASE_URL="$API_URL"
  echo "Resolved baseUrl from AWS: $POSTMAN_BASE_URL"
fi

RUN_ENV="$POSTMAN_DIR/reports/.run-env.json"
mkdir -p "$POSTMAN_DIR/reports"

python3 - <<'PY' "$ENV_FILE" "$RUN_ENV"
import json
import os
import subprocess
import sys

src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as fh:
    env = json.load(fh)

values = {entry.get("key"): entry.get("value", "") for entry in env.get("values", [])}

PLACEHOLDER_URL_MARKERS = (
    "YOUR_API_ID",
    "abc123",
    "example.com",
    "<api-id>",
)
PLACEHOLDER_CREDENTIALS = (
    "YOUR_PASSWORD",
    "replace-me",
    "your-email@example.com",
    "writer@example.com",
)


def is_placeholder_url(url: str) -> bool:
    if not url or not url.startswith("https://"):
        return True
    lowered = url.lower()
    return any(marker.lower() in lowered for marker in PLACEHOLDER_URL_MARKERS)


def resolve_api_url_from_aws() -> str | None:
    try:
        result = subprocess.run(
            [
                "aws",
                "cloudformation",
                "describe-stacks",
                "--stack-name",
                "TechBlogApiStack",
                "--query",
                "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    url = result.stdout.strip().rstrip("/")
    if not url or url == "None":
        return None
    return url


override_url = os.environ.get("POSTMAN_BASE_URL")
env_username = os.environ.get("POSTMAN_USERNAME", "").strip()
env_password = os.environ.get("POSTMAN_PASSWORD", "").strip()
base_url = (override_url or values.get("baseUrl", "")).rstrip("/")
username = env_username or values.get("username", "")
password = env_password or values.get("password", "")

if is_placeholder_url(base_url) and not override_url:
    auto_resolve = os.environ.get("RESOLVE_API_URL_FROM_AWS", "auto")
    if auto_resolve != "0":
        resolved = resolve_api_url_from_aws()
        if resolved:
            base_url = resolved
            override_url = resolved
            print(f"Resolved baseUrl from AWS: {base_url}")

max_ms = os.environ.get("MAX_RESPONSE_MS")
for entry in env.get("values", []):
    key = entry.get("key")
    if key == "baseUrl" and override_url:
        entry["value"] = override_url.rstrip("/")
    elif key == "baseUrl" and base_url and not is_placeholder_url(base_url):
        entry["value"] = base_url
    elif key == "username" and env_username:
        entry["value"] = env_username
    elif key == "password" and env_password:
        entry["value"] = env_password
    if max_ms and key == "maxResponseMs":
        entry["value"] = max_ms

with open(dst, "w", encoding="utf-8") as fh:
    json.dump(env, fh, indent=2)

final_url = next(
    (entry.get("value", "") for entry in env.get("values", []) if entry.get("key") == "baseUrl"),
    "",
)
final_user = next(
    (entry.get("value", "") for entry in env.get("values", []) if entry.get("key") == "username"),
    "",
)
final_pass = next(
    (entry.get("value", "") for entry in env.get("values", []) if entry.get("key") == "password"),
    "",
)

errors: list[str] = []
if is_placeholder_url(final_url):
    errors.append(
        "baseUrl is still a placeholder. Edit postman/environments/local.postman_environment.json "
        "or run with RESOLVE_API_URL_FROM_AWS=1 (requires valid AWS credentials)."
    )
if not final_user or (not env_username and final_user in PLACEHOLDER_CREDENTIALS):
    errors.append(
        "username is missing or still a placeholder. Set POSTMAN_USERNAME (CI) or edit local.postman_environment.json."
    )
if not final_pass or (not env_password and final_pass in PLACEHOLDER_CREDENTIALS):
    errors.append(
        "password is missing or still a placeholder. Set POSTMAN_PASSWORD (CI) or edit local.postman_environment.json."
    )

if errors:
    print("Postman environment is not configured:", file=sys.stderr)
    for message in errors:
        print(f"  - {message}", file=sys.stderr)
    print(file=sys.stderr)
    print(f"Environment file: {src}", file=sys.stderr)
    sys.exit(1)
PY

cd "$POSTMAN_DIR"
if [[ ! -d node_modules ]]; then
  npm install --silent
fi

PERF_ITERATIONS="${PERF_ITERATIONS:-20}"
PERF_DELAY_MS="${PERF_DELAY_MS:-100}"
STAMP=$(date +%Y%m%d-%H%M%S)

case "$MODE" in
  smoke)
    npx newman run "$COLLECTION" \
      -e "$RUN_ENV" \
      --folder "Smoke" \
      --reporters cli
    ;;
  perf|performance)
    npx newman run "$COLLECTION" \
      -e "$RUN_ENV" \
      --folder "Performance - Read APIs" \
      -n "$PERF_ITERATIONS" \
      --delay-request "$PERF_DELAY_MS" \
      --reporters cli,json \
      --reporter-json-export "$POSTMAN_DIR/reports/perf-${STAMP}.json"
    echo "Report: postman/reports/perf-${STAMP}.json"
    ;;
  *)
    echo "Unknown mode: $MODE (use smoke or perf)" >&2
    exit 1
    ;;
esac

rm -f "$RUN_ENV"
