#Requires -Version 5.1
Write-Host ">>> Cleaning caches..." -ForegroundColor Cyan
$paths = @(
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "build", "dist", "htmlcov", ".coverage"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Remove-Item -Recurse -Force $p
        Write-Host "  removed $p" -ForegroundColor DarkGray
    }
}
Get-ChildItem -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object {
        Remove-Item -Recurse -Force $_.FullName
        Write-Host "  removed $($_.FullName)" -ForegroundColor DarkGray
    }
Write-Host "Clean OK" -ForegroundColor Green
