#!/usr/bin/env pwsh
# Quick Deploy Script for AWS Token Generator Integration
# This deploys the token generator as part of your existing infrastructure

param(
    [string]$Email = "23071a66c5@vnrvjiet.in",
    [switch]$Apply,
    [switch]$Plan,
    [switch]$Destroy
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 AWS Stock Pipeline - Token Generator Integration" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════" -ForegroundColor Cyan

# Change to infrastructure directory
Set-Location "$PSScriptRoot\..\infra"

if ($Plan -or (-not $Apply -and -not $Destroy)) {
    Write-Host "📋 Planning deployment..." -ForegroundColor Yellow
    terraform plan -var="notification_email=$Email"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Plan successful! Use -Apply to deploy." -ForegroundColor Green
    } else {
        Write-Host "❌ Plan failed!" -ForegroundColor Red
        exit 1
    }
}

if ($Apply) {
    Write-Host "🚀 Deploying infrastructure with Token Generator..." -ForegroundColor Yellow
    terraform apply -auto-approve -var="notification_email=$Email"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n🎉 Deployment successful!" -ForegroundColor Green
        
        # Get the token generator URL
        $tokenUrl = terraform output -raw token_generator_url 2>$null
        
        if ($tokenUrl) {
            Write-Host "`n🔑 TOKEN GENERATOR READY!" -ForegroundColor Cyan
            Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
            Write-Host "Web UI: $tokenUrl" -ForegroundColor Green
            Write-Host "`n💾 Saving URL to token-generator-url.txt..." -ForegroundColor Yellow
            $tokenUrl | Out-File -FilePath "$PSScriptRoot\..\token-generator-url.txt" -Encoding UTF8
            
            Write-Host "`n📱 DAILY WORKFLOW:" -ForegroundColor Yellow
            Write-Host "1. 🌐 Open: $tokenUrl" -ForegroundColor Cyan
            Write-Host "2. 🔑 Enter Fyers credentials" -ForegroundColor Cyan
            Write-Host "3. ✅ Generate tokens with 3 clicks!" -ForegroundColor Cyan
            Write-Host "`n🎯 No more command-line scripts needed!" -ForegroundColor Green
        }
        
        # Show other useful outputs
        $s3Bucket = terraform output -raw s3_bucket_name 2>$null
        $lambdaFunction = terraform output -raw lambda_function_name 2>$null
        
        if ($s3Bucket) {
            Write-Host "`n📦 PIPELINE RESOURCES:" -ForegroundColor Yellow
            Write-Host "S3 Bucket: $s3Bucket" -ForegroundColor Green
            Write-Host "Lambda Function: $lambdaFunction" -ForegroundColor Green
        }
        
    } else {
        Write-Host "❌ Deployment failed!" -ForegroundColor Red
        exit 1
    }
}

if ($Destroy) {
    Write-Host "⚠️  Destroying infrastructure..." -ForegroundColor Red
    terraform destroy -auto-approve -var="notification_email=$Email"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Infrastructure destroyed successfully." -ForegroundColor Green
    } else {
        Write-Host "❌ Destroy failed!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n════════════════════════════════════════════════════" -ForegroundColor Cyan
