# Team Access Setup (PowerShell Version)
# Usage: .\setup_team_access.ps1 -TeamName "trading-team" -Email "trader@company.com"

param(
    [Parameter(Mandatory=$true)]
    [string]$TeamName,
    
    [Parameter(Mandatory=$true)]
    [string]$Email
)

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

Write-Host "🚀 Setting up Stock Data API access for team: $TeamName" -ForegroundColor Green
Write-Host "📧 Notification email: $Email" -ForegroundColor Yellow

# 1. Create team-specific configuration
Write-Host "📝 Creating team configuration..." -ForegroundColor Blue
$teamConfig = @{
    team_name = $TeamName
    notification_email = $Email
    created_at = $timestamp
    aws_region = "ap-south-1"
    endpoints = @{
    s3_bucket = "stock-pipeline-dev-ohlcv-{SUFFIX}"
    sns_topic = "arn:aws:sns:ap-south-1:{ACCOUNT_ID}:stock-pipeline-alerts"
    }
    access_level = "read_only"
    rate_limits = @{
        s3_requests_per_second = 100
        daily_request_limit = 10000
    }
} | ConvertTo-Json -Depth 4

$teamConfig | Out-File "team_config_$TeamName.json" -Encoding UTF8

# 2. Create environment file
Write-Host "🔧 Creating environment configuration..." -ForegroundColor Blue
$envContent = @"
# Stock Data API Configuration for $TeamName
# Generated on $(Get-Date)

# AWS Configuration
AWS_DEFAULT_REGION=ap-south-1
AWS_PROFILE=default

# Stock Data API Endpoints
STOCK_DATA_BUCKET=stock-pipeline-dev-ohlcv-{REPLACE_WITH_ACTUAL_SUFFIX}
SNS_TOPIC_ARN=arn:aws:sns:ap-south-1:{REPLACE_WITH_ACCOUNT_ID}:stock-pipeline-alerts

# Team Configuration
TEAM_NAME=$TeamName
NOTIFICATION_EMAIL=$Email

# Optional: Custom settings
# CACHE_TTL_SECONDS=300
# MAX_RETRY_ATTEMPTS=3
# LOG_LEVEL=INFO
"@

$envContent | Out-File ".env_$TeamName" -Encoding UTF8

# 3. Create Python requirements file
Write-Host "📦 Creating Python requirements..." -ForegroundColor Blue
$requirementsContent = @"
# Python dependencies for Stock Data API access
boto3>=1.34.0
pandas>=2.0.0
python-dotenv>=1.0.0
requests>=2.31.0

# Optional: For advanced features
plotly>=5.0.0  # For charts
streamlit>=1.28.0  # For dashboards
numpy>=1.24.0  # For numerical analysis
pytz>=2023.3  # For timezone handling
"@

$requirementsContent | Out-File "requirements_$TeamName.txt" -Encoding UTF8

# 4. Create sample Python script
Write-Host "🐍 Creating sample Python script..." -ForegroundColor Blue
$pythonContent = @'
#!/usr/bin/env python3
"""
Sample script for accessing Stock Data API
Customize this for your team's specific needs
"""

import os
from dotenv import load_dotenv
import sys
sys.path.append('.')  # Add current directory to path

# Load environment variables
load_dotenv(f'.env_{os.getenv("TEAM_NAME", "default")}')

def main():
    print(f"🏢 Team: {os.getenv('TEAM_NAME', 'Unknown')}")
    print(f"📊 Bucket: {os.getenv('STOCK_DATA_BUCKET', 'Not configured')}")
    print(f"🔔 SNS Topic: {os.getenv('SNS_TOPIC_ARN', 'Not configured')}")
    
    # Import the stock client
    try:
        from examples.stock_client import StockDataClient
        
        bucket = os.getenv('STOCK_DATA_BUCKET')
        if bucket and 'REPLACE' not in bucket:
            client = StockDataClient(bucket)
            
            # Test connection
            print("\n🧪 Testing connection...")
            latest = client.get_latest_price('RELIANCE')
            if latest:
                print(f"✅ Successfully fetched RELIANCE price: ₹{latest['ohlcv']['close']}")
            else:
                print("⚠️  No data found - check bucket name and permissions")
        else:
            print("⚠️  Please update STOCK_DATA_BUCKET in your .env file")
            
    except ImportError:
        print("❌ Stock client not found. Run from the project root directory.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
'@

$pythonContent | Out-File "sample_$TeamName.py" -Encoding UTF8

# 5. Create IAM policy document
Write-Host "🔐 Creating IAM policy document..." -ForegroundColor Blue
$iamPolicy = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Sid = "StockDataS3ReadAccess"
            Effect = "Allow"
            Action = @(
                "s3:GetObject",
                "s3:ListBucket"
            )
            Resource = @(
                "arn:aws:s3:::stock-pipeline-dev-ohlcv-*",
                "arn:aws:s3:::stock-pipeline-dev-ohlcv-*/*"
            )
        },
        @{
            Sid = "StockDataSNSAccess"
            Effect = "Allow"
            Action = @(
                "sns:Subscribe",
                "sns:Unsubscribe",
                "sns:ListSubscriptions"
            )
            Resource = "arn:aws:sns:ap-south-1:*:stock-pipeline-alerts"
        }
    )
} | ConvertTo-Json -Depth 4

$iamPolicy | Out-File "iam_policy_$TeamName.json" -Encoding UTF8

# 6. Create setup instructions
Write-Host "📋 Creating setup instructions..." -ForegroundColor Blue
$instructionsContent = @"
# Stock Data API Setup Instructions for $TeamName

## Quick Start

1. **Install Python dependencies:**
   ``````bash
   pip install -r requirements_$TeamName.txt
   ``````

2. **Configure AWS credentials:**
   ``````bash
   aws configure
   # Enter your AWS Access Key ID, Secret Key, and set region to ap-south-1
   ``````

3. **Update environment file:**
   - Edit ``.env_$TeamName``
   - Replace ``{REPLACE_WITH_ACTUAL_SUFFIX}`` with actual bucket suffix
   - Replace ``{REPLACE_WITH_ACCOUNT_ID}`` with actual AWS account ID

4. **Set up IAM permissions:**
   - Create IAM policy using ``iam_policy_$TeamName.json``
   - Attach policy to your IAM user/role

5. **Test the setup:**
   ``````bash
   python sample_$TeamName.py
   ``````

## Available Symbols
- RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK
- HINDUNILVR, ITC, LT, BHARTIARTL, KOTAKBANK

## Data Update Frequency
- Every 15 minutes during market hours (9:15 AM - 3:30 PM IST)
- Monday to Friday (excluding holidays)

## Support
- Documentation: API_INTEGRATION_GUIDE.md
- Sample code: examples/ folder
- Contact: data-platform-team@company.com

## Cost Considerations
- S3 GET requests: `$0.0004 per 1,000 requests
- SNS notifications: `$0.50 per 1 million notifications
- Estimated cost for typical usage: `$1-5 per month

## Rate Limits
- S3: 100 requests per second (can be increased)
- Daily limit: 10,000 requests per team
"@

$instructionsContent | Out-File "SETUP_INSTRUCTIONS_$TeamName.md" -Encoding UTF8

Write-Host "✅ Setup complete for team: $TeamName" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Files created:" -ForegroundColor Yellow
Write-Host "   - team_config_$TeamName.json"
Write-Host "   - .env_$TeamName"
Write-Host "   - requirements_$TeamName.txt"
Write-Host "   - sample_$TeamName.py"
Write-Host "   - iam_policy_$TeamName.json"
Write-Host "   - SETUP_INSTRUCTIONS_$TeamName.md"
Write-Host ""
Write-Host "📧 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Share these files with the $TeamName team"
Write-Host "   2. Subscribe $Email to SNS notifications"
Write-Host "   3. Help team set up AWS credentials and IAM permissions"
Write-Host "   4. Provide actual bucket name and account ID"
Write-Host ""
Write-Host "🔗 Share this command with the team:" -ForegroundColor Magenta
Write-Host "   `$env:TEAM_NAME='$TeamName'; python sample_$TeamName.py"
