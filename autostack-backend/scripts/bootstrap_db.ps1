param()

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $scriptDir '..')

$env:PYTHONPATH = '.'

alembic upgrade head
