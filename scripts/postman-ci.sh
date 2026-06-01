#!/usr/bin/env bash
# CI entrypoint for Newman (GitHub Actions deploy jobs).
# Requires POSTMAN_USERNAME and POSTMAN_PASSWORD; resolves baseUrl from TechBlogApiStack.
#
# Usage:
#   POSTMAN_USERNAME=... POSTMAN_PASSWORD=... bash scripts/postman-ci.sh smoke
#   POSTMAN_USERNAME=... POSTMAN_PASSWORD=... PERF_ITERATIONS=10 bash scripts/postman-ci.sh perf
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ -z "${POSTMAN_USERNAME:-}" || -z "${POSTMAN_PASSWORD:-}" ]]; then
  echo "Missing POSTMAN_USERNAME / POSTMAN_PASSWORD." >&2
  echo "Add them to GitHub environment secrets (development + production)." >&2
  exit 1
fi

export RESOLVE_API_URL_FROM_AWS="${RESOLVE_API_URL_FROM_AWS:-1}"
export POSTMAN_ENV_FILE="${POSTMAN_ENV_FILE:-$ROOT/postman/environments/template.postman_environment.json}"

cd "$ROOT/postman"
npm ci --silent
cd "$ROOT"

MODE="${1:-smoke}"
if [[ "$MODE" == "pipeline" ]]; then
  bash scripts/postman-run.sh smoke
  iter="${PERF_ITERATIONS:-10}"
  if [[ "$iter" != "0" ]]; then
    PERF_ITERATIONS="$iter" bash scripts/postman-run.sh perf
  else
    echo "Skipping Postman performance (PERF_ITERATIONS=0)"
  fi
  exit 0
fi

exec bash scripts/postman-run.sh "$MODE"
