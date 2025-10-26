# Alternative Deployment: Using AWS Public Lambda Layer for Pandas
# This approach SKIPS local packaging by using a public Pandas layer

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PACKAGING LAMBDA (LAYER MODE)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# Step 1: Package ONLY the Lambda function (no Pandas)
Write-Host "Step 1: Packaging Lambda function (without Pandas)..." -ForegroundColor Green

$scriptDir = $PSScriptRoot
$projectRoot = Split-Path $scriptDir -Parent
$analyticsDir = Join-Path $projectRoot "analytics"
$deploymentDir = Join-Path $projectRoot "deployment"
$zipFile = Join-Path $deploymentDir "lambda_analytics.zip"

# Check if source exists
$lambdaSource = Join-Path $analyticsDir "lambda_analytics.py"

if (-not (Test-Path $lambdaSource)) {
    Write-Host "ERROR: Lambda function not found at $lambdaSource" -ForegroundColor Red
    exit 1
}

# Remove old package
if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
}

# Create ZIP with just the Lambda function
Compress-Archive -Path $lambdaSource -DestinationPath $zipFile -CompressionLevel Optimal

$zipSizeKB = [math]::Round((Get-Item $zipFile).Length / 1KB, 2)

Write-Host "  Package created: lambda_analytics.zip" -ForegroundColor Gray
Write-Host "  Package size: $zipSizeKB KB (tiny!)" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PACKAGE BUILD COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Update Terraform to use AWS Lambda Layer" -ForegroundColor Gray
Write-Host "  2. Run: cd ..\infra" -ForegroundColor Gray
Write-Host "  3. Run: terraform apply -var=`"notification_email=you@domain.com`"" -ForegroundColor Gray
Write-Host ""
Write-Host "See LAMBDA_LAYER_ALTERNATIVE.md for detailed instructions" -ForegroundColor Yellow
Write-Host ""
