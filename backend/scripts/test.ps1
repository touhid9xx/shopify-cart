#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Write-Host ">>> Running pytest..." -ForegroundColor Cyan
pytest -v
Write-Host "Tests OK" -ForegroundColor Green
