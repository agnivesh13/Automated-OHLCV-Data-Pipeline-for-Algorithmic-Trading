# Package Analytics Lambda with Pandas Layer
# This script builds the Lambda deployment package with Pandas dependencies

param(
    [string]$PythonPath = "python"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PACKAGING ANALYTICS LAMBDA WITH PANDAS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# Directories
$scriptDir = $PSScriptRoot
$projectRoot = Split-Path $scriptDir -Parent
$analyticsDir = Join-Path $projectRoot "analytics"
$deploymentDir = Join-Path $projectRoot "deployment"
$packageDir = Join-Path $deploymentDir "lambda_analytics_package"
$layerDir = Join-Path $packageDir "python"

Write-Host "Cleaning previous build..." -ForegroundColor Yellow
if (Test-Path $packageDir) {
    Remove-Item -Recurse -Force $packageDir
}
New-Item -ItemType Directory -Path $packageDir | Out-Null
New-Item -ItemType Directory -Path $layerDir | Out-Null

# Step 1: Install Pandas and dependencies
Write-Host ""
Write-Host "Step 1: Installing Pandas and dependencies..." -ForegroundColor Green
Write-Host "  This may take 2-3 minutes (downloading ~60 MB)..." -ForegroundColor Gray

$requirementsFile = Join-Path $analyticsDir "requirements.txt"

if (-not (Test-Path $requirementsFile)) {
    Write-Host "ERROR: requirements.txt not found at $requirementsFile" -ForegroundColor Red
    exit 1
}

Write-Host "  Installing to: $layerDir" -ForegroundColor Gray

& $PythonPath -m pip install -r $requirementsFile -t $layerDir --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "  ✓ Dependencies installed" -ForegroundColor Green

# Step 2: Copy Lambda function
Write-Host ""
Write-Host "Step 2: Copying Lambda function code..." -ForegroundColor Green

$lambdaSource = Join-Path $analyticsDir "lambda_analytics.py"
$lambdaDest = Join-Path $packageDir "lambda_analytics.py"

if (-not (Test-Path $lambdaSource)) {
    Write-Host "ERROR: Lambda function not found at $lambdaSource" -ForegroundColor Red
    exit 1
}

Copy-Item $lambdaSource $lambdaDest
Write-Host "  ✓ Lambda function copied" -ForegroundColor Green

# Step 3: Create deployment package
Write-Host ""
Write-Host "Step 3: Creating deployment ZIP..." -ForegroundColor Green

$zipFile = Join-Path $deploymentDir "lambda_analytics.zip"

if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
}

# Change to package directory to create clean ZIP structure
Push-Location $packageDir

try {
    # Add Python dependencies (from python/ directory)
    Write-Host "  Compressing Pandas layer..." -ForegroundColor Gray
    Compress-Archive -Path "python\*" -DestinationPath $zipFile -CompressionLevel Optimal
    
    # Add Lambda function
    Write-Host "  Adding Lambda function..." -ForegroundColor Gray
    Compress-Archive -Path "lambda_analytics.py" -DestinationPath $zipFile -Update
    
    Write-Host "  ✓ Deployment package created" -ForegroundColor Green
}
finally {
    Pop-Location
}

# Step 4: Check package size
Write-Host ""
Write-Host "Step 4: Checking package size..." -ForegroundColor Green

$zipSize = (Get-Item $zipFile).Length
$zipSizeMB = [math]::Round($zipSize / 1MB, 2)

Write-Host "  Package size: $zipSizeMB MB (zipped)" -ForegroundColor Gray

if ($zipSizeMB -gt 50) {
    Write-Host "  ⚠ WARNING: Package exceeds 50 MB Lambda limit!" -ForegroundColor Yellow
    Write-Host "  You may need to use Lambda Layers instead." -ForegroundColor Yellow
}
else {
    Write-Host "  ✓ Package size OK (< 50 MB)" -ForegroundColor Green
}

# Step 5: Calculate unzipped size estimate
$unzippedSize = (Get-ChildItem -Recurse $packageDir | Measure-Object -Property Length -Sum).Sum
$unzippedSizeMB = [math]::Round($unzippedSize / 1MB, 2)

Write-Host "  Unzipped size: $unzippedSizeMB MB (estimated)" -ForegroundColor Gray

if ($unzippedSizeMB -gt 250) {
    Write-Host "  ⚠ WARNING: Unzipped package exceeds 250 MB Lambda limit!" -ForegroundColor Yellow
}
else {
    Write-Host "  ✓ Unzipped size OK (< 250 MB)" -ForegroundColor Green
}

# Cleanup temporary package directory
Write-Host ""
Write-Host "Cleaning up temporary files..." -ForegroundColor Yellow
Remove-Item -Recurse -Force $packageDir

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PACKAGE BUILD COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Deployment package: $zipFile" -ForegroundColor White
Write-Host "Package size: $zipSizeMB MB (zipped), $unzippedSizeMB MB (unzipped)" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. cd infra" -ForegroundColor Gray
Write-Host "  2. terraform apply -var=`"notification_email=you@domain.com`"" -ForegroundColor Gray
Write-Host ""
Write-Host "Query examples:" -ForegroundColor Yellow
Write-Host "  python ..\examples\query_analytics.py" -ForegroundColor Gray
Write-Host ""
