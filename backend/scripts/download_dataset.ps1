# Download NVIDIA Shopify dataset and preprocess into train/val/test splits.
#
# Usage:
#   .\scripts\download_dataset.ps1
#   .\scripts\download_dataset.ps1 -MaxPerClass 500
#   .\scripts\download_dataset.ps1 -ExploreOnly

param(
    [int]$MaxPerClass = 0,       # 0 = no cap
    [switch]$ExploreOnly,
    [switch]$SkipExplore,
    [switch]$SkipDownload
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  NVIDIA Shopify Dataset — Download + Preprocess" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Explore
if (-not $SkipExplore) {
    Write-Host ">>> Step 1/3: Explore class distribution..." -ForegroundColor Yellow
    python -m shopify_cart.ml.dataset --explore
    if ($LASTEXITCODE -ne 0) { throw "Explore failed" }
    Write-Host ""
}

if ($ExploreOnly) {
    Write-Host "Explore-only mode. Done." -ForegroundColor Green
    exit 0
}

# 2. Download
if (-not $SkipDownload) {
    Write-Host ">>> Step 2/3: Download images..." -ForegroundColor Yellow
    if ($MaxPerClass -gt 0) {
        python -m shopify_cart.ml.dataset --download --max-per-class $MaxPerClass
    } else {
        python -m shopify_cart.ml.dataset --download
    }
    if ($LASTEXITCODE -ne 0) { throw "Download failed" }
    Write-Host ""
}

# 3. Preprocess
Write-Host ">>> Step 3/3: Preprocess into train/val/test..." -ForegroundColor Yellow
python -m shopify_cart.ml.preprocess
if ($LASTEXITCODE -ne 0) { throw "Preprocess failed" }
Write-Host ""

Write-Host "===========================================================" -ForegroundColor Green
Write-Host "  Dataset ready at data/processed/" -ForegroundColor Green
Write-Host "===========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next: train a model" -ForegroundColor Cyan
Write-Host "  python -m shopify_cart.ml.train --epochs 5 --batch-size 32" -ForegroundColor Cyan
Write-Host ""
