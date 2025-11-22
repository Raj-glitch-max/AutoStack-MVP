$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSCommandPath
$root = Join-Path $root ".." | Resolve-Path

if (-not $env:DATABASE_URL) { $env:DATABASE_URL = "sqlite+aiosqlite:///$($root.Path)/smoke.db" }
if (-not $env:SECRET_KEY) { $env:SECRET_KEY = "smoke-secret" }
if (-not $env:FRONTEND_URL) { $env:FRONTEND_URL = "http://localhost:3000" }
if (-not $env:AUTOSTACK_DEPLOY_DIR) { $env:AUTOSTACK_DEPLOY_DIR = "$($root.Path)/test_artifacts" }

Set-Location $root
python -m pytest -m smoke @args

