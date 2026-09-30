#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Write-Host ">>> Ruff format..." -ForegroundColor Cyan
ruff format src tests
Write-Host ">>> Ruff check --fix..." -ForegroundColor Cyan
ruff check --fix src tests
Write-Host "Format OK" -ForegroundColor Green
