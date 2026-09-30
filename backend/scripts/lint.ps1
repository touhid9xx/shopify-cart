#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Write-Host ">>> Running Ruff check..." -ForegroundColor Cyan
ruff check src tests
Write-Host ">>> Running Ruff format check..." -ForegroundColor Cyan
ruff format --check src tests
Write-Host ">>> Running Mypy..." -ForegroundColor Cyan
mypy src
Write-Host "Lint OK" -ForegroundColor Green
