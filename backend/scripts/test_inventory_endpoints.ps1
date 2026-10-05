<#
.SYNOPSIS
    Smoke test for admin inventory endpoints.

.DESCRIPTION
    Logs in as an admin user, then exercises every admin inventory endpoint:
      - List (all, low-stock filter)
      - Stats
      - Alerts
      - Reorder suggestions
      - Adjust (positive delta)

.PARAMETER Email
    Admin email. Default: admin@docker.com

.PARAMETER Password
    Admin password. Default: admin12345

.PARAMETER BaseUrl
    Backend base URL. Default: http://localhost:8000

.PARAMETER Token
    Optional pre-existing JWT. If provided, skips login.

.PARAMETER ProductId
    Product to use in the adjust test. Default: auto-pick from list.
#>

param(
    [string] $Email     = "admin@docker.com",
    [string] $Password  = "admin12345",
    [string] $BaseUrl   = "http://localhost:8000",
    [string] $Token     = "",
    [int]    $ProductId = 0
)

$ErrorActionPreference = "Stop"

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
function Write-Section {
    param([string] $Text)
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor DarkGray
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor DarkGray
}

function Test-Endpoint {
    param(
        [string] $Name,
        [string] $Method,
        [string] $Path,
        [string] $Body = ""
    )

    Write-Host ""
    Write-Host "> $Name" -ForegroundColor Cyan
    Write-Host "  $Method $Path" -ForegroundColor DarkGray

    $params = @{
        Method      = $Method
        Uri         = "$BaseUrl$Path"
        Headers     = $script:Headers
        ContentType = "application/json"
    }
    if ($Body) { $params.Body = $Body }

    try {
        $resp = Invoke-RestMethod @params
        $json = $resp | ConvertTo-Json -Depth 5
        Write-Host "  [OK] 200" -ForegroundColor Green
        Write-Host $json -ForegroundColor Gray
        return $resp
    } catch {
        $status = $_.Exception.Response.StatusCode.value__
        $detail = $_.ErrorDetails.Message
        if (-not $detail) { $detail = $_.Exception.Message }
        Write-Host "  [FAIL] $status : $detail" -ForegroundColor Red
        return $null
    }
}

# ----------------------------------------------------------------------
# 0. Login (unless -Token was provided)
# ----------------------------------------------------------------------
Write-Section "0. Login"

if ($Token) {
    Write-Host "  Using provided -Token (skipping login)." -ForegroundColor DarkGray
} else {
    Write-Host "  POST /api/v1/auth/login  ($Email)" -ForegroundColor DarkGray
    try {
        $loginBody = @{ email = $Email; password = $Password } | ConvertTo-Json
        $login = Invoke-RestMethod -Method POST `
            -Uri "$BaseUrl/api/v1/auth/login" `
            -Body $loginBody `
            -ContentType "application/json"

        $Token = $login.access_token
        if (-not $Token) {
            Write-Host "  [FAIL] Login response missing access_token." -ForegroundColor Red
            Write-Host ($login | ConvertTo-Json -Depth 5) -ForegroundColor Gray
            exit 1
        }
        Write-Host "  [OK] Logged in (token length: $($Token.Length))" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Login failed: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.ErrorDetails.Message) {
            Write-Host "  -> $($_.ErrorDetails.Message)" -ForegroundColor Gray
        }
        Write-Host ""
        Write-Host "  Hint: is the backend running at $BaseUrl ?" -ForegroundColor Yellow
        exit 1
    }
}

$script:Headers = @{ Authorization = "Bearer $Token" }

# ----------------------------------------------------------------------
# 1. List inventory
# ----------------------------------------------------------------------
Write-Section "1. List inventory (page 1, size 5)"
$list = Test-Endpoint `
    -Name "List inventory" `
    -Method GET `
    -Path "/api/v1/admin/inventory?page=1&size=5"

# Auto-pick a product ID for the adjust test
$Location = "default"
if ($ProductId -eq 0 -and $list -and $list.items -and $list.items.Count -gt 0) {
    $ProductId = [int] $list.items[0].product_id
    $Location  = [string] $list.items[0].location
    Write-Host "  -> Auto-picked product_id=$ProductId location='$Location'" -ForegroundColor DarkGray
}

if ($ProductId -eq 0) {
    $ProductId = 1
    $Location = "default"
    Write-Host "  -> No items in list; falling back to product_id=1 location='default'" -ForegroundColor Yellow
}

# ----------------------------------------------------------------------
# 2. Low-stock filter
# ----------------------------------------------------------------------
Write-Section "2. Low-stock only"
Test-Endpoint `
    -Name "Low-stock only" `
    -Method GET `
    -Path "/api/v1/admin/inventory?low_stock_only=true&page=1&size=5" | Out-Null

# ----------------------------------------------------------------------
# 3. Stats
# ----------------------------------------------------------------------
Write-Section "3. Stats (KPIs)"
Test-Endpoint `
    -Name "Stats" `
    -Method GET `
    -Path "/api/v1/admin/inventory/stats" | Out-Null

# ----------------------------------------------------------------------
# 4. Alerts
# ----------------------------------------------------------------------
Write-Section "4. Alerts (unresolved)"
Test-Endpoint `
    -Name "Alerts" `
    -Method GET `
    -Path "/api/v1/admin/inventory/alerts?page=1&size=5" | Out-Null

# ----------------------------------------------------------------------
# 5. Reorder suggestions
# ----------------------------------------------------------------------
Write-Section "5. Reorder suggestions"
Test-Endpoint `
    -Name "Reorder suggestions" `
    -Method GET `
    -Path "/api/v1/admin/inventory/reorder-suggestions?low_stock_only=true&limit=5" | Out-Null

# ----------------------------------------------------------------------
# 6. Adjust stock
# ----------------------------------------------------------------------
Write-Section "6. Adjust stock (+10)"
$adjustBody = @{
    product_id = $ProductId
    location   = $Location
    delta      = 10
    reason     = "smoke test"
} | ConvertTo-Json

$adjusted = Test-Endpoint `
    -Name "Adjust +10" `
    -Method POST `
    -Path "/api/v1/admin/inventory/adjust" `
    -Body $adjustBody

if ($adjusted) {
    Write-Host ""
    Write-Host "  New quantity for product $ProductId @ '$Location': $($adjusted.quantity)" -ForegroundColor Green
}

# ----------------------------------------------------------------------
# 7. Guard test - negative resulting stock
# ----------------------------------------------------------------------
Write-Section "7. Guard test (expect 400/409)"
$badBody = @{
    product_id = $ProductId
    location   = $Location
    delta      = -999999
    reason     = "should fail"
} | ConvertTo-Json

$bad = Test-Endpoint `
    -Name "Adjust -999999 (should fail)" `
    -Method POST `
    -Path "/api/v1/admin/inventory/adjust" `
    -Body $badBody

if ($null -eq $bad) {
    Write-Host "  [OK] Guard worked - request was rejected as expected." -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Guard failed - negative stock was allowed!" -ForegroundColor Red
}

# ----------------------------------------------------------------------
# Done
# ----------------------------------------------------------------------
Write-Host ""
Write-Host "[OK] Smoke test complete." -ForegroundColor Green
Write-Host ""
