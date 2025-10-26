# Athena Table Setup Automation Script
# This script automates the Athena table creation process

param(
    [string]$Region = "ap-south-1",
    [string]$Database = "stock_analytics"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Athena Table Setup Automation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Get bucket name from Terraform
Write-Host "Step 1: Getting S3 bucket name from Terraform..." -ForegroundColor Yellow
try {
    Push-Location "$PSScriptRoot\..\infra"
    $bucketName = terraform output -raw s3_bucket_name 2>$null
    Pop-Location
    
    if (-not $bucketName) {
        throw "Could not get bucket name from Terraform"
    }
    
    Write-Host "✓ Bucket name: $bucketName" -ForegroundColor Green
}
catch {
    Write-Host "✗ Error getting bucket name: $_" -ForegroundColor Red
    Write-Host "Please run 'terraform apply' first in the infra directory" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 2: Read SQL template
Write-Host "Step 2: Preparing SQL statements..." -ForegroundColor Yellow
$sqlFile = "$PSScriptRoot\..\sql\athena_lightweight_csv.sql"

if (-not (Test-Path $sqlFile)) {
    Write-Host "✗ SQL file not found: $sqlFile" -ForegroundColor Red
    exit 1
}

$sqlContent = Get-Content $sqlFile -Raw
$sqlContent = $sqlContent -replace 'YOUR_BUCKET_NAME', $bucketName

Write-Host "✓ SQL template prepared" -ForegroundColor Green
Write-Host ""

# Step 3: Create database
Write-Host "Step 3: Creating Athena database..." -ForegroundColor Yellow
$createDbSql = @"
CREATE DATABASE IF NOT EXISTS $Database
COMMENT 'Stock price analytics database'
LOCATION 's3://$bucketName/athena-database/';
"@

# Save to temp file
$tempDbFile = "$env:TEMP\athena_create_db.sql"
$createDbSql | Out-File -FilePath $tempDbFile -Encoding UTF8

Write-Host "Database SQL:" -ForegroundColor Gray
Write-Host $createDbSql -ForegroundColor DarkGray
Write-Host ""

try {
    # Create database using AWS CLI
    $queryExecutionId = aws athena start-query-execution `
        --query-string $createDbSql `
        --result-configuration "OutputLocation=s3://$bucketName/athena-results/" `
        --region $Region `
        --query 'QueryExecutionId' `
        --output text 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create database: $queryExecutionId"
    }
    
    # Wait for query to complete
    Start-Sleep -Seconds 3
    
    $status = aws athena get-query-execution `
        --query-execution-id $queryExecutionId `
        --region $Region `
        --query 'QueryExecution.Status.State' `
        --output text 2>&1
    
    if ($status -eq "SUCCEEDED") {
        Write-Host "✓ Database '$Database' created successfully" -ForegroundColor Green
    }
    else {
        Write-Host "⚠ Database creation status: $status" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "✗ Error creating database: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create the database manually in Athena console:" -ForegroundColor Yellow
    Write-Host $createDbSql -ForegroundColor White
    Write-Host ""
}

Write-Host ""

# Step 4: Instructions for table creation
Write-Host "Step 4: Creating Athena table..." -ForegroundColor Yellow
Write-Host ""
Write-Host "MANUAL STEP REQUIRED:" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "Due to AWS CLI limitations with complex Athena DDL," -ForegroundColor White
Write-Host "please complete the table creation manually:" -ForegroundColor White
Write-Host ""
Write-Host "1. Open Athena Console:" -ForegroundColor Yellow
Write-Host "   https://console.aws.amazon.com/athena/home?region=$Region" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Select database: $Database" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Copy and paste this SQL:" -ForegroundColor Yellow
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

# Extract just the CREATE TABLE statement
$tableStart = $sqlContent.IndexOf("CREATE EXTERNAL TABLE")
$tableEnd = $sqlContent.IndexOf(";", $tableStart) + 1
$createTableSql = $sqlContent.Substring($tableStart, $tableEnd - $tableStart)

Write-Host $createTableSql -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""

# Save full SQL to file for reference
$outputSqlFile = "$PSScriptRoot\..\sql\athena_configured_${Database}.sql"
$sqlContent | Out-File -FilePath $outputSqlFile -Encoding UTF8

Write-Host "✓ Full SQL saved to: $outputSqlFile" -ForegroundColor Green
Write-Host ""

# Step 5: Create helper script to open Athena console
Write-Host "Step 5: Creating helper scripts..." -ForegroundColor Yellow

$helperScript = @"
# Quick helper to open Athena console
`$url = "https://console.aws.amazon.com/athena/home?region=$Region"
Write-Host "Opening Athena console in browser..." -ForegroundColor Cyan
Start-Process `$url
Write-Host ""
Write-Host "Database: $Database" -ForegroundColor Yellow
Write-Host "Bucket: $bucketName" -ForegroundColor Yellow
Write-Host ""
Write-Host "SQL file: $outputSqlFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "Copy the SQL from the file above and paste into Athena query editor." -ForegroundColor White
"@

$helperScriptFile = "$PSScriptRoot\open-athena-console.ps1"
$helperScript | Out-File -FilePath $helperScriptFile -Encoding UTF8

Write-Host "✓ Helper script created: $helperScriptFile" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SETUP SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ Bucket: $bucketName" -ForegroundColor Green
Write-Host "✓ Database: $Database" -ForegroundColor Green
Write-Host "✓ SQL file: $outputSqlFile" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Run: .\scripts\open-athena-console.ps1" -ForegroundColor White
Write-Host "2. In Athena console, select database: $Database" -ForegroundColor White
Write-Host "3. Open SQL file and copy CREATE TABLE statement" -ForegroundColor White
Write-Host "4. Paste and run in Athena query editor" -ForegroundColor White
Write-Host "5. Test with: SELECT * FROM ohlcv_csv LIMIT 10;" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

# Offer to open console
Write-Host ""
$openConsole = Read-Host "Open Athena console now? (Y/N)"
if ($openConsole -eq 'Y' -or $openConsole -eq 'y') {
    Start-Process "https://console.aws.amazon.com/athena/home?region=$Region"
    Write-Host "✓ Athena console opened in browser" -ForegroundColor Green
}

Write-Host ""
Write-Host "Setup preparation complete! ✨" -ForegroundColor Green
