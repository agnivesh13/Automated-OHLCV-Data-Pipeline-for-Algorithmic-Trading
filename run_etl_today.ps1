# Run ETL Lambda for Today's Date
# Usage: .\run_etl_today.ps1

$today = Get-Date -Format "yyyy-MM-dd"

Write-Host "Running ETL for date: $today" -ForegroundColor Cyan
Write-Host ""

# Create payload object and convert to JSON
$payload = @{
    date = $today
} | ConvertTo-Json -Compress

Write-Host "Payload: $payload" -ForegroundColor Gray

# Save to file with UTF8 (no BOM)
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText("$PSScriptRoot\etl_payload.json", $payload, $utf8NoBom)

Write-Host ""
Write-Host "Invoking Lambda..." -ForegroundColor Yellow

# Invoke Lambda
aws lambda invoke `
    --function-name stock-pipeline-mvp-etl `
    --payload fileb://etl_payload.json `
    response.json

Write-Host ""
Write-Host "Response:" -ForegroundColor Yellow
Get-Content response.json | ConvertFrom-Json | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "ETL invocation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To verify CSV files created, run:" -ForegroundColor Cyan
Write-Host 'aws s3 ls "s3://stock-pipeline-mvp-dev-ohlcv-5e23bf76/analytics/csv/partition_date='$today'/" --recursive' -ForegroundColor White
