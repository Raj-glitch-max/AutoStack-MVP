#!/usr/bin/env bash
set -euo pipefail

# Change to project root (backend)
cd "$(dirname "$0")/.."

# Ensure PYTHONPATH so Alembic can import app.*
export PYTHONPATH=.

alembic upgrade head
