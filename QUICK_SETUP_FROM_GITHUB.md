# 🚀 Quick Setup Guide - Deploy from GitHub

**Complete guide to clone this project from GitHub and deploy to your AWS account**

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:
- [ ] AWS Account (with free tier available)
- [ ] Email address for notifications
- [ ] Fyers API account with credentials

---

## 🔧 Step 1: Install Required Tools

### Windows (PowerShell)
```powershell
# Install AWS CLI
winget install Amazon.AWSCLI

# Install Terraform
winget install Hashicorp.Terraform

# Install Git (if not installed)
winget install Git.Git

# Restart PowerShell after installation
```

### macOS
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install tools
brew install awscli terraform git
```

### Linux (Ubuntu/Debian)
```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform git
```

### Verify Installations
```bash
aws --version       # Should show: aws-cli/2.x.x
terraform version   # Should show: Terraform v1.x.x
git --version       # Should show: git version 2.x.x
```

---

## ☁️ Step 2: Configure AWS Credentials

### 2.1 Get AWS Access Keys
1. Login to [AWS Console](https://console.aws.amazon.com)
2. Go to **IAM** → **Users** → **Create user**
3. Username: `terraform-deployer`
4. Select: **Provide user access to the AWS Management Console** - optional
5. Attach policy: **AdministratorAccess** (for development)
6. Click **Create user**
7. Go to **Security credentials** tab
8. Click **Create access key**
9. Choose **Command Line Interface (CLI)**
10. **Download CSV** or copy the keys

### 2.2 Configure AWS CLI
```bash
aws configure
```

**Enter when prompted:**
- AWS Access Key ID: `[Your Access Key from step 2.1]`
- AWS Secret Access Key: `[Your Secret Access Key from step 2.1]`
- Default region name: `ap-south-1` (Mumbai - free tier optimized)
- Default output format: `json`

### 2.3 Verify Configuration
```bash
aws sts get-caller-identity
```

**Expected output:**
```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/terraform-deployer"
}
```

---

## 📥 Step 3: Clone the Repository

### Get the Repository
```bash
# Clone from GitHub (replace with actual repository URL)
git clone https://github.com/snehinadepu24/Price-Feed-Parser-10.git

# Navigate to project directory
cd Price-Feed-Parser-10
```

### Verify Project Structure
```bash
# Windows PowerShell
dir

# macOS/Linux
ls -la
```

**You should see:**
- `infra/` - Terraform infrastructure files
- `ingestion/` - Lambda ingestion code
- `etl/` - ETL processing code
- `aws-token-generator/` - Token management UI
- `README.md` - Main documentation
- `QUICK_SETUP_FROM_GITHUB.md` - This file

---

## 🚀 Step 4: Deploy Infrastructure

### Option A: Quick Deploy (Recommended for beginners)

**Windows PowerShell:**
```powershell
# Navigate to infrastructure folder
cd infra

# Initialize Terraform
terraform init

# Review what will be created (optional but recommended)
terraform plan -var="notification_email=your-email@example.com"

# Deploy infrastructure
terraform apply -var="notification_email=your-email@example.com"

# Type 'yes' when prompted to confirm
```

**macOS/Linux:**
```bash
# Navigate to infrastructure folder
cd infra

# Initialize Terraform
terraform init

# Review what will be created (optional but recommended)
terraform plan -var="notification_email=your-email@example.com"

# Deploy infrastructure
terraform apply -var="notification_email=your-email@example.com"

# Type 'yes' when prompted to confirm
```

### What Gets Created
The deployment creates these **FREE TIER** resources:
- ✅ **S3 Bucket** - For storing raw JSON data and analytics CSV files
- ✅ **Lambda Functions** (3):
  - `stock-pipeline-mvp-ingestion` - Fetches data every 5 min during trading hours
  - `stock-pipeline-mvp-etl` - Processes data daily at 4 PM IST
  - `stock-pipeline-mvp-api-handler` - REST API for data queries
- ✅ **EventBridge Schedules** - Automated execution triggers
- ✅ **SSM Parameter Store** - Secure credential storage (FREE)
- ✅ **SNS Topic** - Email notifications
- ✅ **CloudWatch Logs** - Monitoring and debugging
- ✅ **API Gateway** - REST API endpoints
- ✅ **IAM Roles** - Security permissions

**Deployment Time:** 3-5 minutes

### Save Terraform Outputs
```bash
# View all outputs
terraform output

# Save to file for reference
terraform output > deployment-info.txt
```

**Important outputs to note:**
- `s3_bucket_name` - Your data storage bucket
- `api_gateway_url` - Your REST API endpoint
- `fyers_parameter_prefix` - Where to store Fyers credentials
- `token_generator_url` - Token management UI

---

## 🔑 Step 5: Configure Fyers API Credentials

### 5.1 Get Fyers Credentials
If you don't have Fyers API credentials yet:
1. Login to [Fyers](https://fyers.in)
2. Go to **API** section → **Create New App**
3. App Type: **Web App**
4. Redirect URL: `https://trade.fyers.in/api-login`
5. Note down:
   - Client ID (format: `ABC123-100`)
   - App Secret
   - Refresh Token (see [TOKEN_MANAGEMENT_GUIDE.md](TOKEN_MANAGEMENT_GUIDE.md))

### 5.2 Store Credentials in AWS SSM Parameter Store

**Get the parameter prefix from Terraform:**
```bash
terraform output fyers_parameter_prefix
# Output: /stock-pipeline-mvp/fyers/
```

**Store credentials (replace with YOUR actual values):**
```bash
# Client ID
aws ssm put-parameter \
  --name "/stock-pipeline-mvp/fyers/client_id" \
  --value "YOUR_CLIENT_ID" \
  --type "SecureString" \
  --overwrite

# App Secret
aws ssm put-parameter \
  --name "/stock-pipeline-mvp/fyers/app_secret" \
  --value "YOUR_APP_SECRET" \
  --type "SecureString" \
  --overwrite

# Refresh Token
aws ssm put-parameter \
  --name "/stock-pipeline-mvp/fyers/refresh_token" \
  --value "YOUR_REFRESH_TOKEN" \
  --type "SecureString" \
  --overwrite

# PIN (optional - only if your Fyers account requires it)
aws ssm put-parameter \
  --name "/stock-pipeline-mvp/fyers/pin" \
  --value "YOUR_PIN" \
  --type "SecureString" \
  --overwrite
```

### 5.3 Verify Credentials Stored
```bash
# List all Fyers parameters
aws ssm get-parameters-by-path \
  --path "/stock-pipeline-mvp/fyers" \
  --with-decryption

# Or check in AWS Console:
# Services → Systems Manager → Parameter Store
```

---

## 🧪 Step 6: Test the Deployment

### 6.1 Test Ingestion Lambda
```bash
# Get Lambda function name
terraform output lambda_function_name

# Invoke manually
aws lambda invoke \
  --function-name stock-pipeline-mvp-ingestion \
  --payload '{}' \
  response.json

# View response
cat response.json
```

**Expected output (during trading hours):**
```json
{
  "statusCode": 200,
  "message": "Successfully ingested data for 10 symbols"
}
```

**Expected output (outside trading hours):**
```json
{
  "statusCode": 200,
  "message": "Outside trading hours - skipping ingestion"
}
```

### 6.2 Check CloudWatch Logs
```bash
# View ingestion logs
aws logs tail /aws/lambda/stock-pipeline-mvp-ingestion --follow

# View ETL logs
aws logs tail /aws/lambda/stock-pipeline-mvp-etl --follow
```

**What to look for:**
- ✅ "Successfully retrieved Fyers API credentials from SSM"
- ✅ "Fetched data for NSE:SBIN-EQ" (and other symbols)
- ✅ "Successfully uploaded data to s3://..."

### 6.3 Verify Data in S3
```bash
# Get bucket name
terraform output s3_bucket_name

# List raw data files
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/Raw\ data/Prices/ --recursive

# List analytics CSV files (after ETL runs at 4 PM IST)
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/analytics/csv/ --recursive
```

### 6.4 Test API Gateway
```bash
# Get API URL
terraform output api_gateway_url

# Test symbols endpoint
curl "$(terraform output -raw api_gateway_url)/symbols"

# Test latest data
curl "$(terraform output -raw api_gateway_url)/latest?symbols=NSE:SBIN-EQ"

# Test historical data (after some data is collected)
curl "$(terraform output -raw api_gateway_url)/historical?symbol=NSE:SBIN-EQ&from=2025-10-24&to=2025-10-24&interval=5"
```

### 6.5 Confirm Email Subscription
1. **Check your email inbox** (the email you provided during deployment)
2. Look for email from **AWS Notifications**
3. Subject: "AWS Notification - Subscription Confirmation"
4. **Click the confirmation link**
5. You should see: "Subscription confirmed!"

---

## 📊 Step 7: Monitor Your Pipeline

### CloudWatch Dashboard
Get the dashboard URL:
```bash
terraform output cloudwatch_dashboard_url
```

Or manually:
1. Go to [CloudWatch Console](https://console.aws.amazon.com/cloudwatch)
2. Click **Dashboards** → `stock-pipeline-mvp-mvp-dashboard`
3. Monitor:
   - Lambda invocations
   - Errors
   - Duration
   - Data ingestion metrics

### S3 Console
Get the S3 console URL:
```bash
terraform output s3_console_url
```

Or manually:
1. Go to [S3 Console](https://s3.console.aws.amazon.com/s3)
2. Find bucket: `stock-pipeline-mvp-dev-ohlcv-XXXXXXXX`
3. Browse folders:
   - `Raw data/Prices/` - Raw JSON files from Fyers API
   - `analytics/csv/` - Processed CSV files (after ETL runs)

### Email Notifications
You'll receive emails for:
- ✅ Successful data ingestion (every 5 min during trading hours)
- ✅ ETL processing completion (daily at 4 PM IST)
- ⚠️ Lambda errors or failures
- 💰 Budget alerts (50% and 80% of $5 monthly cap)

---

## 🔄 How the Pipeline Works

### Automatic Execution Schedule

**Ingestion Lambda:**
- **When:** Every 5 minutes during trading hours
- **Trading Hours:** Monday-Friday, 9:15 AM - 3:30 PM IST
- **What it does:**
  1. Fetches 5-minute OHLCV data from Fyers API
  2. Stores raw JSON in S3 `Raw data/Prices/YYYY-MM-DD/`
  3. Sends success/failure notification

**ETL Lambda:**
- **When:** Daily at 4:00 PM IST (after market close)
- **What it does:**
  1. Reads today's raw JSON files from S3
  2. Converts to partitioned CSV.gz format
  3. Stores in S3 `analytics/csv/symbol=X/year=Y/month=M/day=D/`
  4. Sends completion notification

**API Handler Lambda:**
- **When:** On-demand via API Gateway requests
- **What it does:**
  1. Serves real-time data queries
  2. Returns JSON or CSV format
  3. Supports symbol lists, latest data, historical queries

### Data Flow
```
Fyers API (Market Data)
    ↓
Ingestion Lambda (every 5 min during trading hours)
    ↓
S3: Raw data/Prices/YYYY-MM-DD/raw_TIMESTAMP.json
    ↓
ETL Lambda (daily at 4 PM IST)
    ↓
S3: analytics/csv/symbol=X/year=Y/month=M/day=D/data.csv.gz
    ↓
API Gateway / Manual Query
```

---

## 📖 Step 8: Query Your Data

### Option 1: REST API (Recommended)
```bash
# Get your API URL
API_URL=$(terraform output -raw api_gateway_url)

# List all available symbols
curl "$API_URL/symbols"

# Get latest data for specific symbols
curl "$API_URL/latest?symbols=NSE:SBIN-EQ,NSE:RELIANCE-EQ"

# Get historical data for 1 year (CSV format)
curl "$API_URL/historical?symbol=NSE:SBIN-EQ&from=2024-10-24&to=2025-10-24&interval=5" > data.csv

# Get data for specific date range (JSON format)
curl "$API_URL/ohlcv/NSE:SBIN-EQ?from=2025-10-20&to=2025-10-24&interval=5"
```

### Option 2: Download from S3
```bash
# Download all data for local analysis
aws s3 sync s3://$(terraform output -raw s3_bucket_name)/analytics/csv/ ./local_data/

# Decompress CSV files
gunzip local_data/**/*.csv.gz

# Analyze with Python/Excel
```

### Option 3: AWS Athena (Optional - for SQL queries)
See [README.md](README.md) for Athena setup instructions.

---

## 💰 Cost Monitoring

### View Current Costs
```bash
# Check AWS Billing
# Go to: https://console.aws.amazon.com/billing

# Free Tier usage
# Go to: https://console.aws.amazon.com/billing/home#/freetier
```

### Expected Costs
- **Within Free Tier:** $0.00/month
- **Free Tier Limits:**
  - Lambda: 1M requests/month (you'll use ~30K)
  - S3: 5GB storage (you'll use ~50MB first month)
  - CloudWatch: 5GB logs (you'll use ~500MB)
  - SNS: 1,000 emails (you'll use ~200)

### Budget Alerts
Terraform automatically created budget alerts:
- 50% of $5 monthly budget
- 80% of $5 monthly budget

You'll receive emails if costs exceed these thresholds.

---

## 🔧 Maintenance & Operations

### Manual ETL Trigger (Process Specific Date)
```bash
# Process yesterday's data
aws lambda invoke \
  --function-name stock-pipeline-mvp-etl \
  --payload '{"date": "2025-10-23"}' \
  response-etl.json

cat response-etl.json
```

### Update Fyers Credentials
```bash
# Update refresh token (when it expires)
aws ssm put-parameter \
  --name "/stock-pipeline-mvp/fyers/refresh_token" \
  --value "NEW_REFRESH_TOKEN" \
  --type "SecureString" \
  --overwrite
```

### Pause the Pipeline
```bash
# Disable ingestion schedule
aws events disable-rule --name stock-pipeline-mvp-ingestion-schedule

# Disable ETL schedule
aws events disable-rule --name stock-pipeline-mvp-etl-schedule
```

### Resume the Pipeline
```bash
# Enable ingestion schedule
aws events enable-rule --name stock-pipeline-mvp-ingestion-schedule

# Enable ETL schedule
aws events enable-rule --name stock-pipeline-mvp-etl-schedule
```

### View Logs for Specific Time Range
```bash
# Logs from last 1 hour
aws logs tail /aws/lambda/stock-pipeline-mvp-ingestion \
  --since 1h \
  --follow

# Logs from specific date
aws logs filter-log-events \
  --log-group-name /aws/lambda/stock-pipeline-mvp-ingestion \
  --start-time $(date -d "2025-10-24 09:00:00" +%s)000 \
  --end-time $(date -d "2025-10-24 10:00:00" +%s)000
```

---

## 🧹 Cleanup (Destroy Resources)

**⚠️ WARNING: This will delete ALL data and resources!**

```bash
# Navigate to infra folder
cd infra

# Destroy all resources
terraform destroy -var="notification_email=your-email@example.com"

# Type 'yes' when prompted to confirm
```

**Before destroying, consider:**
- Download important data from S3
- Export CloudWatch logs if needed
- Save any analysis results

---

## 📚 Additional Resources

### Documentation Files
- [README.md](README.md) - Complete project overview
- [README-MVP.md](README-MVP.md) - MVP deployment details
- [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md) - Detailed beginner tutorial
- [TOKEN_MANAGEMENT_GUIDE.md](TOKEN_MANAGEMENT_GUIDE.md) - Fyers token setup
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - API endpoint reference

### Useful Links
- [AWS Free Tier](https://aws.amazon.com/free/)
- [Terraform Documentation](https://www.terraform.io/docs)
- [Fyers API Documentation](https://myapi.fyers.in/docs/)
- [AWS CLI Reference](https://docs.aws.amazon.com/cli/)

---

## ❓ Troubleshooting

### Issue: "Access Denied" errors
**Solution:**
```bash
# Verify AWS credentials
aws sts get-caller-identity

# If fails, reconfigure
aws configure
```

### Issue: Lambda function errors
**Solution:**
```bash
# Check logs
aws logs tail /aws/lambda/stock-pipeline-mvp-ingestion --follow

# Common causes:
# - Incorrect Fyers credentials in SSM
# - Expired refresh token
# - API rate limits
```

### Issue: No data in S3
**Solution:**
```bash
# Verify Lambda is running during trading hours (9:15-15:30 IST)
# Outside trading hours, ingestion is skipped (this is normal)

# Check EventBridge schedule
aws events list-rules --name-prefix "stock-pipeline-mvp"

# Check Lambda logs for errors
aws logs tail /aws/lambda/stock-pipeline-mvp-ingestion --follow
```

### Issue: Terraform errors
**Solution:**
```bash
# Initialize again
terraform init -upgrade

# Check state
terraform state list

# Force unlock if locked
terraform force-unlock LOCK_ID
```

### Issue: Email notifications not received
**Solution:**
1. Check spam/junk folder
2. Verify SNS subscription confirmed
3. Check SNS topic in AWS Console
4. Verify email in terraform output: `terraform output sns_topic_arn`

---

## 🎉 Success Checklist

After completing this guide, you should have:
- ✅ AWS account configured with credentials
- ✅ Terraform initialized and applied successfully
- ✅ Lambda functions deployed and executing
- ✅ Fyers credentials stored in SSM Parameter Store
- ✅ Data collecting in S3 bucket
- ✅ Email notifications working
- ✅ API Gateway endpoints accessible
- ✅ CloudWatch monitoring active
- ✅ Budget alerts configured
- ✅ $0.00 monthly cost (within free tier)

**Congratulations!** Your AWS Stock Price Feed Pipeline is now running! 🚀📊

---

**Questions or Issues?**
Check CloudWatch logs first - they usually contain detailed error messages and troubleshooting hints.
