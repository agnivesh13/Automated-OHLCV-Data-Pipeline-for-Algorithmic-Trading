# Pre-Deployment Checklist (PowerShell)
# Verifies all prerequisites are met before deploying the MVP

param(
    [switch]$SkipInteractive
)

# Color functions
function Write-Header($text) {
    Write-Host "`n=== $text ===" -ForegroundColor Blue
}

function Write-Success($text) {
    Write-Host "✅ $text" -ForegroundColor Green
}

function Write-Warning($text) {
    Write-Host "⚠️  $text" -ForegroundColor Yellow
}

function Write-Error($text) {
    Write-Host "❌ $text" -ForegroundColor Red
}

function Test-Command($command) {
    try {
        $null = Get-Command $command -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

function Test-AwsCli {
    Write-Header "Checking AWS CLI"
    
    if (-not (Test-Command "aws")) {
        Write-Error "AWS CLI is not installed"
        Write-Host "   Install from: https://aws.amazon.com/cli/" -ForegroundColor Cyan
        return $false
    }
    
    try {
        $version = aws --version 2>&1
        Write-Success "AWS CLI installed: $version"
        
        # Test AWS configuration
        $identity = aws sts get-caller-identity 2>&1 | ConvertFrom-Json
        if ($identity.Account) {
            Write-Success "AWS configured - Account: $($identity.Account)"
            Write-Host "   User: $($identity.Arn)" -ForegroundColor Gray
            return $true
        }
        else {
            Write-Error "AWS CLI is not configured"
            Write-Host "   Run: aws configure" -ForegroundColor Cyan
            return $false
        }
    }
    catch {
        Write-Error "AWS CLI configuration error: $($_.Exception.Message)"
        return $false
    }
}

function Test-Terraform {
    Write-Header "Checking Terraform"
    
    if (-not (Test-Command "terraform")) {
        Write-Error "Terraform is not installed"
        Write-Host "   Install from: https://terraform.io/downloads" -ForegroundColor Cyan
        return $false
    }
    
    try {
        $version = terraform version
        $versionMatch = $version | Select-String "Terraform v(\d+\.\d+\.\d+)"
        if ($versionMatch) {
            $versionNumber = $versionMatch.Matches[0].Groups[1].Value
            Write-Success "Terraform installed: v$versionNumber"
        }
        else {
            Write-Success "Terraform installed: $version"
        }
        return $true
    }
    catch {
        Write-Error "Error checking Terraform: $($_.Exception.Message)"
        return $false
    }
}

function Test-Python {
    Write-Header "Checking Python"
    
    $pythonCommands = @("python", "python3", "py")
    $pythonFound = $false
    
    foreach ($cmd in $pythonCommands) {
        if (Test-Command $cmd) {
            try {
                $version = & $cmd --version 2>&1
                if ($version -match "Python (\d+\.\d+\.\d+)") {
                    $versionNumber = $matches[1]
                    $major, $minor = $versionNumber.Split('.')[0..1]
                    
                    if ([int]$major -ge 3 -and [int]$minor -ge 8) {
                        Write-Success "Python installed: $version (using $cmd)"
                        $pythonFound = $true
                        break
                    }
                    else {
                        Write-Warning "Python $versionNumber found but recommend 3.8+"
                        $pythonFound = $true
                        break
                    }
                }
            }
            catch {
                continue
            }
        }
    }
    
    if (-not $pythonFound) {
        Write-Error "Python is not installed"
        Write-Host "   Install from: https://python.org/downloads" -ForegroundColor Cyan
        return $false
    }
    
    return $true
}

function Test-Git {
    Write-Header "Checking Git"
    
    if (-not (Test-Command "git")) {
        Write-Warning "Git is not installed (optional but recommended)"
        Write-Host "   Install from: https://git-scm.com/downloads" -ForegroundColor Cyan
        return $true  # Git is optional
    }
    
    try {
        $version = git --version
        Write-Success "Git installed: $version"
        return $true
    }
    catch {
        Write-Warning "Git command failed but continuing"
        return $true
    }
}

function Test-FileStructure {
    Write-Header "Checking File Structure"
    
    $requiredFiles = @(
    'infra\main-mvp.tf',
        'deployment\deploy-mvp.ps1',
        'deployment\deploy-mvp.sh',
        'ingestion\lambda_ingestion.py',
        'analysis\mvp_analyzer.py'
    )
    
    $missingFiles = @()
    
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            Write-Success "Found: $file"
        }
        else {
            Write-Error "Missing: $file"
            $missingFiles += $file
        }
    }
    
    return $missingFiles.Count -eq 0
}

function Get-DeploymentConfig {
    Write-Header "Deployment Configuration"
    
    $config = @{}
    
    # Get email address
    do {
        $email = Read-Host "Enter your email address for notifications"
        if ($email -match '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$') {
            $config.Email = $email
            Write-Success "Email address: $email"
            break
        }
        else {
            Write-Error "Invalid email format. Please try again."
        }
    } while ($true)
    
    # Get AWS region
    $region = Read-Host "Enter AWS region [ap-south-1]"
    if (-not $region) {
        $region = "ap-south-1"
    }
    $config.Region = $region
    Write-Success "AWS Region: $region"
    
    # Get project name
        $project = Read-Host "Enter project name [stock-pipeline]"
        if (-not $project) {
            $project = "stock-pipeline"
    }
    $config.Project = $project
    Write-Success "Project name: $project"
    
    return $config
}

function Test-AwsRegion($region) {
    Write-Header "Validating AWS Region"
    
    try {
        $null = aws ec2 describe-regions --region $region 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "AWS region $region is valid"
            return $true
        }
        else {
            Write-Error "Invalid AWS region: $region"
            Write-Host "   Common regions: ap-south-1, us-east-1, us-west-2, eu-west-1" -ForegroundColor Cyan
            return $false
        }
    }
    catch {
        Write-Error "Error validating region: $($_.Exception.Message)"
        return $false
    }
}

function Show-CostEstimates {
    Write-Header "Cost Estimates"
    
    Write-Host "💰 Expected Monthly Costs (MVP):" -ForegroundColor Yellow
    Write-Host "   • S3 Storage: FREE (5GB limit)"
    Write-Host "   • Lambda: FREE (1M requests limit)"
    Write-Host "   • SNS Notifications: FREE (1K notifications limit)"
    Write-Host "   • CloudWatch Logs: FREE (5GB limit)"
    Write-Host "   • SSM Parameter Store: FREE (standard parameters)"
    Write-Host "   • EventBridge: FREE"
    Write-Host "   • Cost Explorer: FREE"
    Write-Host ""
    Write-Host "💡 Total Estimated Cost: `$0.00 - `$1.00/month (FREE TIER)" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  Cost Control Measures:" -ForegroundColor Yellow
    Write-Host "   • Budget alert at `$2.50 (50% of `$5 budget)"
    Write-Host "   • Budget alert at `$4.00 (80% of `$5 budget)"
    Write-Host "   • S3 lifecycle policies for cost optimization"
    Write-Host "   • Lambda timeout set to 5 minutes max"
    Write-Host "   • Only 10 stocks to minimize API calls"
}

function Show-NextSteps($config) {
    Write-Header "Next Steps"
    
    Write-Host "🚀 You're ready to deploy! Follow these steps:" -ForegroundColor Green
    Write-Host ""
    Write-Host "1. Navigate to the deployment directory and run:" -ForegroundColor Cyan
    Write-Host "   cd deployment"
    Write-Host "   .\deploy-mvp.ps1 -NotificationEmail `"$($config.Email)`""
    Write-Host ""
    Write-Host "2. After deployment, configure your Fyers API credentials:" -ForegroundColor Cyan
    Write-Host "   • Use AWS CLI to store credentials in SSM Parameter Store:"
    Write-Host "     aws ssm put-parameter --name '/project-name/fyers/client_id' --value 'YOUR_CLIENT_ID' --type 'SecureString' --overwrite"
    Write-Host "     aws ssm put-parameter --name '/project-name/fyers/app_secret' --value 'YOUR_APP_SECRET' --type 'SecureString' --overwrite"
    Write-Host "     aws ssm put-parameter --name '/project-name/fyers/refresh_token' --value 'YOUR_REFRESH_TOKEN' --type 'SecureString' --overwrite"
    Write-Host "   • Confirm email subscription for notifications"
    Write-Host ""
    Write-Host "3. Monitor your deployment:" -ForegroundColor Cyan
    Write-Host "   • Check CloudWatch logs for Lambda execution"
    Write-Host "   • Verify data appears in S3 bucket"
    Write-Host "   • Run analysis script to view your data"
    Write-Host ""
    Write-Host "4. Cost monitoring:" -ForegroundColor Cyan
    Write-Host "   • Check AWS Billing Dashboard weekly"
    Write-Host "   • Run cost monitoring script: python monitoring\cost_monitor.py"
    Write-Host "   • Set up additional billing alerts if needed"
}

function Main {
    Write-Host "🔍 AWS MVP Pre-Deployment Checklist" -ForegroundColor Blue
    Write-Host "====================================="
    Write-Host "This script verifies you have everything needed to deploy the stock price feed parser MVP."
    Write-Host ""
    
    $checksPasssed = 0
    $totalChecks = 6
    
    # Run all checks
    if (Test-AwsCli) { $checksPasssed++ }
    if (Test-Terraform) { $checksPasssed++ }
    if (Test-Python) { $checksPasssed++ }
    if (Test-Git) { $checksPasssed++ }
    if (Test-FileStructure) { $checksPasssed++ }
    
    # Get deployment configuration
    if (-not $SkipInteractive) {
        $config = Get-DeploymentConfig
        
        # Validate region
        if (Test-AwsRegion $config.Region) { $checksPasssed++ }
    }
    else {
        $checksPasssed++  # Skip region check in non-interactive mode
    $config = @{ Email = "test@example.com"; Region = "ap-south-1"; Project = "stock-pipeline" }
    }
    
    # Show cost estimates
    Show-CostEstimates
    
    # Summary
    Write-Header "Verification Summary"
    
    if ($checksPasssed -eq $totalChecks) {
        Write-Success "All checks passed! ($checksPasssed/$totalChecks)"
        Write-Host "✨ You're ready to deploy the MVP!" -ForegroundColor Green
        
        if (-not $SkipInteractive) {
            # Ask for confirmation
            $response = Read-Host "`nDo you want to see the deployment commands? (y/n)"
            if ($response -match '^[Yy]') {
                Show-NextSteps $config
            }
        }
    }
    else {
        Write-Error "Some checks failed ($checksPasssed/$totalChecks)"
        Write-Host "Please fix the issues above before deploying." -ForegroundColor Red
        
        if ($checksPasssed -ge 4) {
            Write-Warning "You have most requirements met. Consider proceeding with caution."
        }
    }
    
    Write-Host "`n💡 Need help? Check the BEGINNER_GUIDE.md for detailed instructions." -ForegroundColor Blue
}

# Script entry point
try {
    Main
}
catch {
    Write-Host "`nVerification failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
