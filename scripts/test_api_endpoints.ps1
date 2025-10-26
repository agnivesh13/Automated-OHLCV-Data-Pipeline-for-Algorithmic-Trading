# Quick API Test Script
# Tests all API endpoints to verify they work without Athena

$API_URL = "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "TESTING API ENDPOINTS (NO ATHENA)" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Test 1: Get Symbols
Write-Host "Test 1: GET /symbols" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$API_URL/symbols?limit=5" -Method Get
    Write-Host "  Status: SUCCESS" -ForegroundColor Green
    Write-Host "  Symbols found: $($response.count)" -ForegroundColor Gray
    if ($response.symbols) {
        Write-Host "  Sample: $($response.symbols -join ', ')" -ForegroundColor Gray
    }
}
catch {
    Write-Host "  Status: FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 2: Get OHLCV (will work once ingestion runs)
Write-Host "Test 2: GET /ohlcv/RELIANCE" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$API_URL/ohlcv/RELIANCE?limit=10" -Method Get
    Write-Host "  Status: SUCCESS" -ForegroundColor Green
    Write-Host "  Candles found: $($response.count)" -ForegroundColor Gray
    if ($response.data) {
        Write-Host "  Latest close: $($response.data[-1].close)" -ForegroundColor Gray
    }
}
catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 404) {
        Write-Host "  Status: NO DATA (run ingestion first)" -ForegroundColor Yellow
    }
    else {
        Write-Host "  Status: FAILED - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""

# Test 3: Get Latest
Write-Host "Test 3: GET /latest" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$API_URL/latest" -Method Get
    Write-Host "  Status: SUCCESS" -ForegroundColor Green
    Write-Host "  Symbols: $($response.count)" -ForegroundColor Gray
}
catch {
    Write-Host "  Status: FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 4: Get Historical
Write-Host "Test 4: GET /historical" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$API_URL/historical?symbol=RELIANCE" -Method Get
    Write-Host "  Status: SUCCESS" -ForegroundColor Green
    Write-Host "  Total records: $($response.total_records)" -ForegroundColor Gray
}
catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 404) {
        Write-Host "  Status: NO DATA (run ingestion first)" -ForegroundColor Yellow
    }
    else {
        Write-Host "  Status: FAILED - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""

# Test 5: Alfa Endpoint
Write-Host "Test 5: GET /alfaquantz/price/get" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$API_URL/alfaquantz/price/get?symbol=infy&interval=1d&period=30d" -Method Get
    Write-Host "  Status: SUCCESS" -ForegroundColor Green
    Write-Host "  Candles: $($response.count)" -ForegroundColor Gray
}
catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 404) {
        Write-Host "  Status: NO DATA (run ingestion first)" -ForegroundColor Yellow
    }
    else {
        Write-Host "  Status: FAILED - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "API TEST COMPLETE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Set up Fyers credentials in Token Generator" -ForegroundColor Gray
Write-Host "  2. Run ingestion Lambda manually to get data" -ForegroundColor Gray
Write-Host "  3. Re-run this test to see populated responses" -ForegroundColor Gray
Write-Host ""
Write-Host "Token Generator: https://4z97iyyil4.execute-api.ap-south-1.amazonaws.com/prod" -ForegroundColor White
Write-Host "API Base URL: $API_URL" -ForegroundColor White
Write-Host ""
