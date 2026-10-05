# Smoke test for admin ML insights endpoints.
# Usage: .\scripts\test_ml_insights_endpoints.ps1 -Token "<admin-jwt>"

param(
    [Parameter(Mandatory = $true)] [string] $Token,
    [string] $BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
$headers = @{ Authorization = "Bearer $Token" }

function Test-Endpoint {
    param([string] $Name, [string] $Method, [string] $Path)
    Write-Host "`n>>> $Name" -ForegroundColor Cyan
    Write-Host "$Method $Path" -ForegroundColor Gray
    try {
        $resp = Invoke-RestMethod -Method $Method -Uri "$BaseUrl$Path" -Headers $headers
        $resp | ConvertTo-Json -Depth 5 | Write-Host
        Write-Host "✅ OK" -ForegroundColor Green
        return $resp
    } catch {
        Write-Host "❌ FAILED: $_" -ForegroundColor Red
        return $null
    }
}

Write-Host "`n═══ ML Insights Smoke Test ═══" -ForegroundColor Yellow

# 1. Summary
$summary = Test-Endpoint -Name "Summary" -Method GET -Path "/api/v1/admin/ml/summary"

# 2. Demand forecast (top 5 most urgent)
Test-Endpoint -Name "Demand forecast (top 5)" -Method GET `
    -Path "/api/v1/admin/ml/demand-forecast?page=1&size=5"

# 3. Demand forecast (low stock only)
Test-Endpoint -Name "Demand forecast (low stock)" -Method GET `
    -Path "/api/v1/admin/ml/demand-forecast?low_stock_only=true&size=5"

# 4. Anomalies (top 10)
Test-Endpoint -Name "Anomalies (top 10)" -Method GET `
    -Path "/api/v1/admin/ml/anomalies?page=1&size=10"

# 5. Anomalies (strict threshold)
Test-Endpoint -Name "Anomalies (z >= 2.5)" -Method GET `
    -Path "/api/v1/admin/ml/anomalies?z_threshold=2.5&size=10"

Write-Host "`n✅ Smoke test complete." -ForegroundColor Green
