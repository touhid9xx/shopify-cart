#Requires -Version 5.1
<#
.SYNOPSIS
    Clean up Docker resources for shopify-cart.
.PARAMETER All
    Remove volumes too (⚠️ deletes MySQL data!)
#>
param([switch]$All)

$ErrorActionPreference = "Stop"

Write-Host ">>> Stopping all containers..." -ForegroundColor Cyan
docker compose down --remove-orphans

Write-Host ">>> Removing local shopify-cart image..." -ForegroundColor Cyan
docker rmi shopify-cart:local 2>$null

if ($All) {
    Write-Host ">>> Removing volumes (⚠️ data will be lost)..." -ForegroundColor Yellow
    docker compose down -v
    Write-Host ">>> Removing mlruns folder..." -ForegroundColor Yellow
    if (Test-Path mlruns) {
        Rename-Item mlruns "mlruns_deleted_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    }
}

Write-Host "Clean OK" -ForegroundColor Green
