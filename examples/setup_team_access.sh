#!/bin/bash

# Setup script for teams to quickly configure access to stock data API
# Usage: ./setup_team_access.sh <team-name> <email>

set -e

TEAM_NAME=$1
EMAIL=$2

if [ -z "$TEAM_NAME" ] || [ -z "$EMAIL" ]; then
    echo "Usage: $0 <team-name> <email>"
    echo "Example: $0 trading-team trader@company.com"
    exit 1
fi

echo "🚀 Setting up Stock Data API access for team: $TEAM_NAME"
echo "📧 Notification email: $EMAIL"

# 1. Create team-specific configuration
echo "📝 Creating team configuration..."
cat > "team_config_${TEAM_NAME}.json" << EOF
{
  "team_name": "$TEAM_NAME",
  "notification_email": "$EMAIL",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "aws_region": "ap-south-1",
  "endpoints": {
    "s3_bucket": "stock-pipeline-dev-ohlcv-{SUFFIX}",
    "sns_topic": "arn:aws:sns:ap-south-1:{ACCOUNT_ID}:stock-pipeline-alerts"
  },
  "access_level": "read_only",
  "rate_limits": {
    "s3_requests_per_second": 100,
    "daily_request_limit": 10000
  }
}
EOF

# 2. Create environment file
echo "🔧 Creating environment configuration..."
cat > ".env_${TEAM_NAME}" << EOF
# Stock Data API Configuration for $TEAM_NAME
# Generated on $(date)

# AWS Configuration
AWS_DEFAULT_REGION=ap-south-1
AWS_PROFILE=default

# Stock Data API Endpoints
STOCK_DATA_BUCKET=stock-pipeline-dev-ohlcv-{REPLACE_WITH_ACTUAL_SUFFIX}
SNS_TOPIC_ARN=arn:aws:sns:ap-south-1:{REPLACE_WITH_ACCOUNT_ID}:stock-pipeline-alerts

# Team Configuration
TEAM_NAME=$TEAM_NAME
NOTIFICATION_EMAIL=$EMAIL

# Optional: Custom settings
# CACHE_TTL_SECONDS=300
# MAX_RETRY_ATTEMPTS=3
# LOG_LEVEL=INFO
EOF

# 3. Create Python requirements file
echo "📦 Creating Python requirements..."
cat > "requirements_${TEAM_NAME}.txt" << EOF
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
EOF

# 4. Create sample Python script
echo "🐍 Creating sample Python script..."
cat > "sample_${TEAM_NAME}.py" << 'EOF'
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
EOF

# 5. Create IAM policy document
echo "🔐 Creating IAM policy document..."
cat > "iam_policy_${TEAM_NAME}.json" << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "StockDataS3ReadAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::stock-pipeline-dev-ohlcv-*",
                "arn:aws:s3:::stock-pipeline-dev-ohlcv-*/*"
            ]
        },
        {
            "Sid": "StockDataSNSAccess",
            "Effect": "Allow",
            "Action": [
                "sns:Subscribe",
                "sns:Unsubscribe",
                "sns:ListSubscriptions"
            ],
            "Resource": "arn:aws:sns:ap-south-1:*:stock-pipeline-alerts"
        }
    ]
}
EOF

# 6. Create setup instructions
echo "📋 Creating setup instructions..."
cat > "SETUP_INSTRUCTIONS_${TEAM_NAME}.md" << EOF
# Stock Data API Setup Instructions for $TEAM_NAME

## Quick Start

1. **Install Python dependencies:**
   \`\`\`bash
   pip install -r requirements_${TEAM_NAME}.txt
   \`\`\`

2. **Configure AWS credentials:**
   \`\`\`bash
   aws configure
   # Enter your AWS Access Key ID, Secret Key, and set region to ap-south-1
   \`\`\`

3. **Update environment file:**
   - Edit \`.env_${TEAM_NAME}\`
   - Replace \`{REPLACE_WITH_ACTUAL_SUFFIX}\` with actual bucket suffix
   - Replace \`{REPLACE_WITH_ACCOUNT_ID}\` with actual AWS account ID

4. **Set up IAM permissions:**
   - Create IAM policy using \`iam_policy_${TEAM_NAME}.json\`
   - Attach policy to your IAM user/role

5. **Test the setup:**
   \`\`\`bash
   python sample_${TEAM_NAME}.py
   \`\`\`

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
- S3 GET requests: \$0.0004 per 1,000 requests
- SNS notifications: \$0.50 per 1 million notifications
- Estimated cost for typical usage: \$1-5 per month

## Rate Limits
- S3: 100 requests per second (can be increased)
- Daily limit: 10,000 requests per team
EOF

echo "✅ Setup complete for team: $TEAM_NAME"
echo ""
echo "📁 Files created:"
echo "   - team_config_${TEAM_NAME}.json"
echo "   - .env_${TEAM_NAME}"
echo "   - requirements_${TEAM_NAME}.txt"
echo "   - sample_${TEAM_NAME}.py"
echo "   - iam_policy_${TEAM_NAME}.json"
echo "   - SETUP_INSTRUCTIONS_${TEAM_NAME}.md"
echo ""
echo "📧 Next steps:"
echo "   1. Share these files with the $TEAM_NAME team"
echo "   2. Subscribe $EMAIL to SNS notifications"
echo "   3. Help team set up AWS credentials and IAM permissions"
echo "   4. Provide actual bucket name and account ID"
echo ""
echo "🔗 Share this command with the team:"
echo "   export TEAM_NAME=$TEAM_NAME && python sample_${TEAM_NAME}.py"
