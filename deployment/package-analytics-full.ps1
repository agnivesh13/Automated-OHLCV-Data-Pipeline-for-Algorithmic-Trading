# Package Lambda Analytics with Pandas - Full Package (no layer)
# This packages EVERYTHING including Pandas (~45 MB)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "   LAMBDA ANALYTICS PACKAGER (FULL)"  -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

# Paths
$scriptDir = $PSScriptRoot
$deploymentDir = $scriptDir
$analyticsDir = Join-Path (Split-Path $scriptDir -Parent) "analytics"
$packageDir = Join-Path $deploymentDir "analytics_package"
$zipFile = Join-Path $deploymentDir "lambda_analytics.zip"

# Step 1: Install Python dependencies
Write-Host "Step 1: Installing Pandas and dependencies (~5 minutes)..." -ForegroundColor Green
Write-Host "  This downloads ~60 MB from PyPI..." -ForegroundColor Yellow
Write-Host ""

# Create package directory
if (Test-Path $packageDir) {
    Remove-Item -Recurse -Force $packageDir
}
New-Item -ItemType Directory -Path $packageDir | Out-Null

# Install dependencies to package directory (use binary wheels, no compilation)
Write-Host "  Running pip install..." -ForegroundColor Gray
pip install --target $packageDir --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.11 pandas==2.0.3 numpy --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    Write-Host "Trying with default installation method..." -ForegroundColor Yellow
    pip install --target $packageDir --only-binary=:all: pandas==2.0.3 numpy
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
}

Write-Host "  + Dependencies installed" -ForegroundColor Green

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
Write-Host "  + Lambda function copied" -ForegroundColor Green

# Step 3: Create deployment package
Write-Host ""
Write-Host "Step 3: Creating deployment ZIP..." -ForegroundColor Green

if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
}

# Change to package directory to create clean ZIP structure
Push-Location $packageDir

try {
    Write-Host "  Compressing package (this may take a minute)..." -ForegroundColor Gray
    
    # Compress all files in package directory
    Get-ChildItem -Path . -Recurse | Compress-Archive -DestinationPath $zipFile -CompressionLevel Optimal
    
    Write-Host "  + Deployment package created" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Failed to create ZIP package" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Pop-Location
    exit 1
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
    Write-Host "  ! WARNING: Package exceeds 50 MB Lambda limit!" -ForegroundColor Yellow
    Write-Host "  You may need to use Lambda Layers instead." -ForegroundColor Yellow
}
else {
    Write-Host "  + Package size OK (< 50 MB)" -ForegroundColor Green
}

# Step 5: Calculate unzipped size estimate
$unzippedSize = (Get-ChildItem -Recurse $packageDir | Measure-Object -Property Length -Sum).Sum
$unzippedSizeMB = [math]::Round($unzippedSize / 1MB, 2)

Write-Host "  Unzipped size: $unzippedSizeMB MB (estimated)" -ForegroundColor Gray

if ($unzippedSizeMB -gt 250) {
    Write-Host "  ! WARNING: Unzipped package exceeds 250 MB Lambda limit!" -ForegroundColor Yellow
}
else {
    Write-Host "  + Unzipped size OK (< 250 MB)" -ForegroundColor Green
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
Write-Host "Package location: $zipFile" -ForegroundColor White
Write-Host "Package size: $zipSizeMB MB" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. cd ..\infra" -ForegroundColor White
Write-Host "  2. terraform apply" -ForegroundColor White
Write-Host ""
