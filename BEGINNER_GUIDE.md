# 🚀 Complete Beginner's Guide to Deploy Stock Price Feed Parser MVP

**Step-by-Step AWS Deployment for Absolute Beginners**

This guide assumes you have **zero AWS experience** and will walk you through everything from account creation to monitoring your deployed application.

## 📋 Table of Contents
1. [AWS Account Setup](#1-aws-account-setup)
2. [Install Required Tools](#2-install-required-tools)
3. [Get Fyers API Credentials](#3-get-fyers-api-credentials)
4. [Configure AWS](#4-configure-aws)
5. [Deploy the Application](#5-deploy-the-application)
6. [Configure API Credentials](#6-configure-api-credentials)
7. [Monitor Your Application](#7-monitor-your-application)
8. [Analyze Your Data](#8-analyze-your-data)
9. [Troubleshooting](#9-troubleshooting)
10. [Cost Management](#10-cost-management)

---

## 1. AWS Account Setup

### Step 1.1: Create AWS Account
1. **Go to AWS**: Visit [aws.amazon.com](https://aws.amazon.com)
2. **Click "Create an AWS Account"**
3. **Fill out the form**:
   - Email address (use a valid email you check regularly)
   - Password (make it strong!)
   - AWS account name (e.g., "MyStockTracker")
4. **Choose "Personal"** account type
5. **Enter contact information**
6. **Payment information**: 
   - ⚠️ **IMPORTANT**: Even though we're using free tier, AWS requires a credit card
   - Your card won't be charged if you stay within free tier limits
7. **Phone verification**: AWS will call/text you with a verification code
8. **Choose Support Plan**: Select **"Basic support - Free"**

### Step 1.2: Secure Your Account
1. **Enable MFA (Multi-Factor Authentication)**:
   - Go to AWS Console → Your Name (top right) → "My Security Credentials"
   - Click "Assign MFA device"
   - Use your phone's authenticator app (Google Authenticator, Authy, etc.)

### Step 1.3: Set Up Billing Alerts
1. **Go to Billing Dashboard**: [console.aws.amazon.com/billing](https://console.aws.amazon.com/billing)
2. **Click "Billing Preferences"**
3. **Enable**:
   - ✅ Receive PDF Invoice By Email
   - ✅ Receive Free Tier Usage Alerts
   - ✅ Receive Billing Alerts
4. **Enter your email address**
5. **Save preferences**

---

## 2. Install Required Tools

### Step 2.1: Install AWS CLI

**For Windows:**
1. Download AWS CLI installer: [awscli.amazonaws.com/AWSCLIV2.msi](https://awscli.amazonaws.com/AWSCLIV2.msi)
2. Run the installer
3. Open PowerShell and verify: `aws --version`

**For Mac:**
```bash
# Install using Homebrew
brew install awscli

# Or download installer from AWS website
```

**For Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### Step 2.2: Install Terraform

**For Windows:**
1. Go to [terraform.io/downloads](https://terraform.io/downloads)
2. Download Windows 64-bit version
3. Extract to `C:\terraform\`
4. Add `C:\terraform\` to your PATH environment variable
5. Open new PowerShell and verify: `terraform version`

**For Mac:**
```bash
# Install using Homebrew
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

**For Linux:**
```bash
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

### Step 2.3: Install Python (if not already installed)
1. Go to [python.org/downloads](https://python.org/downloads)
2. Download Python 3.8 or newer
3. **IMPORTANT**: Check "Add Python to PATH" during installation
4. Verify installation: `python --version`

### Step 2.4: Install Git (if not already installed)
1. Go to [git-scm.com/downloads](https://git-scm.com/downloads)
2. Install Git
3. Verify: `git --version`

---

## 3. Get Fyers API Credentials

### Step 3.1: Create Fyers Account
1. **Visit**: [fyers.in](https://fyers.in)
2. **Sign up** for a trading account
3. **Complete KYC verification** (this may take 1-2 days)

### Step 3.2: Get API Credentials
1. **Login to Fyers**
2. **Go to**: "API" section (usually under "Developer" or "Tools")
3. **Create API App**:
   - App Name: "Stock Price Tracker"
   - App Type: "Web App"
   - Redirect URL: `https://trade.fyers.in/api-login`
4. **Note down**:
   - Client ID (looks like: `ABC123-100`)
   - App Secret
   - API Key

### Step 3.3: Generate Access Token
1. **Follow Fyers documentation** to generate access token
2. **You'll need**:
   - Access Token (expires daily, needs refresh)
   - Refresh Token (to get new access tokens)
   - Client ID

⚠️ **Keep these credentials secure!** Never share them or commit them to code.

---

## 4. Configure AWS

### Step 4.1: Create IAM User (Recommended for beginners)
1. **Go to AWS Console**: [console.aws.amazon.com](https://console.aws.amazon.com)
2. **Search for "IAM"** in the search box
3. **Click "Users"** → **"Create user"**
4. **Username**: `terraform-user`
5. **Attach policies**:
   - Search and select: `AdministratorAccess`
   - ⚠️ **Note**: This gives full access. In production, use more restrictive policies.
6. **Click "Next"** → **"Create user"**

### Step 4.2: Create Access Keys
1. **Click on your new user** (`terraform-user`)
2. **Go to "Security credentials" tab**
3. **Click "Create access key"**
4. **Choose "Command Line Interface (CLI)"**
5. **Check the confirmation box**
6. **Click "Create access key"**
7. **Download the CSV file** or copy the keys:
   - Access key ID (starts with `AKIA...`)
   - Secret access key (long random string)

⚠️ **CRITICAL**: Save these keys securely. You can't view the secret key again!

### Step 4.3: Configure AWS CLI
Open PowerShell/Terminal and run:
```bash
aws configure
```

**Enter when prompted**:
- AWS Access Key ID: `[your access key]`
- AWS Secret Access Key: `[your secret key]`
- Default region name: `ap-south-1`
- Default output format: `json`

**Verify configuration**:
```bash
aws sts get-caller-identity
```
You should see your account ID and user info.

---

## 5. Deploy the Application

### Step 5.1: Download the Code
```bash
# Clone the project from GitHub
git clone https://github.com/snehinadepu24/Price-Feed-Parser-10.git
cd Price-Feed-Parser-10

# OR download as ZIP:
# 1. Visit: https://github.com/snehinadepu24/Price-Feed-Parser-10
# 2. Click "Code" → "Download ZIP"
# 3. Extract and navigate to the folder
```

### Step 5.2: Review the MVP Configuration
1. **Open** `infra/main-mvp.tf` in a text editor
2. **Review the services** that will be created:
   - S3 bucket for data storage
   - Lambda function for data collection
   - SNS topic for email notifications
   - Secrets Manager for API credentials
   - Cost budget alerts

### Step 5.3: Deploy Using PowerShell (Windows)
```powershell
# Navigate to project root
cd "Price Feed Parser"

# Navigate to infrastructure folder
cd infra

# Initialize Terraform
terraform init

# Plan deployment (review what will be created)
terraform plan -var="notification_email=your-email@example.com"

# Deploy infrastructure
terraform apply -var="notification_email=your-email@example.com"

# Type 'yes' when prompted to confirm
```

**Replace `your-email@example.com` with your actual email address!**

### Step 5.4: Deploy Using Bash (Mac/Linux)
```bash
# Navigate to project root
cd "Price Feed Parser"

# Navigate to infrastructure folder
cd infra

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var="notification_email=your-email@example.com"

# Deploy infrastructure  
terraform apply -var="notification_email=your-email@example.com"

# Type 'yes' when prompted to confirm
```

### Step 5.5: What Happens During Deployment
The script will:
1. ✅ Check prerequisites (AWS CLI, Terraform)
2. ✅ Validate AWS credentials
3. ✅ Create Lambda deployment package
4. ✅ Initialize Terraform
5. ✅ Plan infrastructure deployment
6. ✅ Deploy AWS resources
7. ✅ Show deployment summary

**This process takes 5-15 minutes.**

### Step 5.6: Deployment Success
When successful, you'll see:
```
🎉 MVP Deployment Complete!
==========================

📊 Deployed Resources (Free Tier):
   • S3 Bucket: stock-pipeline-dev-ohlcv-[random]
   • Lambda Function: stock-pipeline-ingestion
   • SNS Topic: arn:aws:sns:ap-south-1:[account]:stock-pipeline-alerts
   • Secrets Manager: stock-pipeline-fyers-credentials
```

**Save these resource names!** You'll need them for the next steps.

---

## 6. Configure API Credentials

### Step 6.1: Update SSM Parameter Store
**Option A: Using AWS Console (Easier for beginners)**
1. **Go to AWS Console** → Search "Systems Manager" or "SSM"
2. **Click "Parameter Store"** in the left sidebar
3. **Find parameters starting with** `/stock-pipeline-mvp/fyers/`
4. **Click on** `/stock-pipeline-mvp/fyers/client_id`
5. **Click "Edit"**
6. **Update the value** with your actual client ID
7. **Click "Save changes"**
8. **Repeat for**:
   - `/stock-pipeline-mvp/fyers/app_secret`
   - `/stock-pipeline-mvp/fyers/refresh_token`
   - `/stock-pipeline-mvp/fyers/pin` (optional)

**Option B: Using AWS CLI**
```bash
# Set all parameters at once
aws ssm put-parameter \
  --name "/stock-pipeline-mvp/fyers/client_id" \
  --value "YOUR_CLIENT_ID" \
  --type "SecureString" \
  --overwrite

aws ssm put-parameter \
  --name "/stock-pipeline-mvp/fyers/app_secret" \
  --value "YOUR_APP_SECRET" \
  --type "SecureString" \
  --overwrite

aws ssm put-parameter \
  --name "/stock-pipeline-mvp/fyers/refresh_token" \
  --value "YOUR_REFRESH_TOKEN" \
  --type "SecureString" \
  --overwrite

aws ssm put-parameter \
  --name "/stock-pipeline-mvp/fyers/pin" \
  --value "YOUR_PIN" \
  --type "SecureString" \
  --overwrite
```

### Step 6.2: Confirm Email Subscription
1. **Check your email** for SNS subscription confirmation
2. **Click the confirmation link** in the email
3. You should see "Subscription confirmed!"

---

## 7. Monitor Your Application

### Step 7.1: Test Lambda Function
1. **Go to AWS Console** → Search "Lambda"
2. **Click on** `stock-pipeline-ingestion`
3. **Click "Test"**
4. **Create new test event**:
   - Name: `manual-test`
   - Keep default JSON: `{}`
5. **Click "Test"**

**Expected Result**: Function should run successfully and you should receive an email notification.

### Step 7.2: Check CloudWatch Logs
1. **In Lambda console**, click "Monitor" tab
2. **Click "View CloudWatch logs"**
3. **Click on the latest log stream**
4. **Review the logs** for any errors

**What to look for**:
- ✅ "Successfully retrieved Fyers API credentials"
- ✅ "Fetched data for [symbol]"
- ✅ "Successfully uploaded MVP data to s3://"

### Step 7.3: Verify S3 Data Storage
1. **Go to AWS Console** → Search "S3"
2. **Click on your bucket** (name from deployment output)
3. **Navigate to** `Raw data/Prices/` folder
4. **You should see folders** organized by year/month/day
5. **Download a JSON file** to verify data structure

### Step 7.4: Monitor Scheduled Execution
The Lambda function runs automatically every 15 minutes. Check:
1. **Lambda console** → "Monitor" tab for execution history
2. **Your email** for success/failure notifications
3. **S3 bucket** for new data files

---

## 8. Analyze Your Data

### Step 8.1: Set Up Analysis Environment
```bash
# Install required Python packages
pip install pandas matplotlib seaborn boto3

# Navigate to analysis folder
cd analysis
```

### Step 8.2: Configure Analysis Script
```bash
# Set your S3 bucket name (from deployment output)
# Windows PowerShell:
$env:S3_BUCKET_NAME = "your-bucket-name-here"

# Mac/Linux:
export S3_BUCKET_NAME="your-bucket-name-here"
```

### Step 8.3: Run Analysis
```bash
python mvp_analyzer.py
```

**Expected Output**:
- 📊 Charts showing price trends
- 📋 Statistical reports
- 📁 Analysis folder with visualizations

### Step 8.4: Review Generated Reports
The script creates:
- `price_trends.png` - Stock price movements
- `volume_analysis.png` - Trading volume by stock
- `correlation_heatmap.png` - Stock correlation matrix
- `analysis_report.txt` - Detailed text summary
- `processed_data.csv` - Raw data for further analysis

---

## 9. Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Access Denied" Errors
**Cause**: Insufficient AWS permissions
**Solution**:
```bash
# Verify your AWS credentials
aws sts get-caller-identity

# If this fails, reconfigure AWS CLI
aws configure
```

#### Issue 2: Lambda Function Fails
**Cause**: Usually incorrect API credentials
**Solution**:
1. Check CloudWatch logs for specific error
2. Verify Fyers API credentials in Secrets Manager
3. Ensure access token is not expired

#### Issue 3: No Data in S3
**Cause**: API rate limits or connection issues
**Solution**:
1. Check Lambda logs for HTTP errors
2. Verify Fyers API credentials
3. Ensure you have active market data subscription

#### Issue 4: High Costs
**Cause**: Exceeding free tier limits
**Solution**:
```bash
# Check current costs
python monitoring/cost_monitor.py

# Review AWS billing dashboard
# Consider reducing Lambda frequency
```

#### Issue 5: Terraform Errors
**Cause**: Resource conflicts or AWS service limits
**Solution**:
```bash
# Check Terraform state
cd infra
terraform plan -var="notification_email=your-email@example.com" main-mvp.tf

# If errors, try:
terraform refresh
terraform apply -var="notification_email=your-email@example.com" main-mvp.tf
```

### Getting Help
1. **Check CloudWatch Logs** first - they usually contain the error details
2. **AWS Documentation**: [docs.aws.amazon.com](https://docs.aws.amazon.com)
3. **Fyers API Documentation**: Check Fyers developer portal
4. **AWS Support**: Use AWS forums for free tier questions

---

## 10. Cost Management

### Step 10.1: Monitor Free Tier Usage
1. **Go to AWS Billing Console**
2. **Click "Free Tier"** in left sidebar
3. **Review usage** for each service
4. **Set up alerts** if approaching limits

### Step 10.2: Set Up Cost Alerts
```bash
# Run cost monitoring script
cd monitoring
python cost_monitor.py
```

### Step 10.3: Expected Costs
- **Month 1-12**: $0.40 - $2.00/month (mostly Secrets Manager)
- **After Free Tier expires**: $3-5/month

### Step 10.4: Cost Optimization Tips
1. **Reduce Lambda frequency** if needed (15 min → 30 min)
2. **Limit stock symbols** (current: 10 stocks)
3. **Set up S3 lifecycle policies** for old data
4. **Monitor CloudWatch log retention**

### Step 10.5: Emergency Cost Control
If costs exceed expectations:
```bash
# Pause the system by disabling the schedule
aws events disable-rule --name stock-pipeline-ingestion-schedule

# To re-enable later:
aws events enable-rule --name stock-pipeline-ingestion-schedule
```

---

## 🎯 Next Steps After Successful Deployment

### Immediate (First Week)
1. ✅ Verify data collection is working
2. ✅ Check email notifications
3. ✅ Run analysis script daily
4. ✅ Monitor costs

### Short Term (First Month)
1. 📊 Analyze stock patterns from collected data
2. 🔧 Fine-tune Lambda function frequency
3. 💰 Optimize costs based on usage
4. 📱 Set up mobile alerts (optional)

### Long Term (After Free Tier)
1. 🚀 Scale up by enabling commented services:
   - RDS for structured storage
   - ECS for advanced processing
   - Glue for ETL pipelines
   - Athena for SQL analytics
2. 📈 Add more stocks and data sources
3. 🤖 Implement trading algorithms (if licensed)
4. ☁️ Move to production-grade infrastructure

---

## 📞 Support Checklist

If you get stuck, work through this checklist:

### Basic Verification
- [ ] AWS CLI configured and working: `aws sts get-caller-identity`
- [ ] Terraform installed: `terraform version`
- [ ] Python installed: `python --version`
- [ ] Email confirmed for SNS notifications

### Deployment Verification
- [ ] All Terraform resources created successfully
- [ ] S3 bucket exists and accessible
- [ ] Lambda function created
- [ ] Secrets Manager contains API credentials
- [ ] SNS topic subscription confirmed

### Functional Verification
- [ ] Lambda function executes without errors
- [ ] Data appears in S3 bucket
- [ ] Email notifications received
- [ ] Analysis script runs successfully

### Cost Verification
- [ ] Free tier usage monitored
- [ ] Billing alerts configured
- [ ] No unexpected charges
- [ ] Budget notifications working

---

**🎉 Congratulations!** You've successfully deployed a production-ready stock data pipeline on AWS using best practices and free tier optimization!

Remember: This MVP demonstrates the full system architecture while keeping costs minimal. When you're ready to scale, simply uncomment the production services in the Terraform configuration.
