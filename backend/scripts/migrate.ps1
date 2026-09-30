#Requires -Version 5.1
param(
    [string]$Message = "auto migration"
)
$ErrorActionPreference = "Stop"
Write-Host ">>> Alembic upgrade head..." -ForegroundColor Cyan
alembic upgrade head
Write-Host ">>> Alembic revision --autogenerate -m '$Message'..." -ForegroundColor Cyan
alembic revision --autogenerate -m "$Message"
Write-Host "Migration OK" -ForegroundColor Green
