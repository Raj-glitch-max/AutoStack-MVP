#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///$ROOT_DIR/smoke.db}"
export SECRET_KEY="${SECRET_KEY:-smoke-secret}"
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
export AUTOSTACK_DEPLOY_DIR="${AUTOSTACK_DEPLOY_DIR:-$ROOT_DIR/test_artifacts}"

cd "$ROOT_DIR"
python -m pytest -m smoke "$@"

