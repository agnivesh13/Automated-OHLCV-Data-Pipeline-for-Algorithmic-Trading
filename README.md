# AWS Stock Price Feed Pipeline - MVP Edition

A cost-conscious AWS data pipeline for ingesting and processing stock OHLCV (Open, High, Low, Close, Volume) data from the Fyers API with **automatic token management**. This MVP uses AWS Free Tier services to keep costs at $0/month while demonstrating full pipeline functionality.

**🚀 Quick Start:** See [QUICK_SETUP_FROM_GITHUB.md](QUICK_SETUP_FROM_GITHUB.md) for complete GitHub clone and deployment instructions.

**📦 GitHub Repository:** [https://github.com/snehinadepu24/Price-Feed-Parser-10](https://github.com/snehinadepu24/Price-Feed-Parser-10)

## 🧭 What's Included in the MVP
- **Ingestion Lambda** scheduled by EventBridge every 5 minutes during trading hours, persisting raw JSON to S3
- **Lightweight ETL Lambda** producing compressed CSV files (NO Pandas/PyArrow - pure Python + boto3)
- **Token generator web UI** backed by API Gateway + Lambda, storing secrets in SSM Parameter Store
- **SNS email alerts** and **CloudWatch logs** for monitoring
- **Terraform configuration** 100% free-tier optimized (Mumbai region compatible)

---

## 🚀 Getting Started

### 1. Deploy the Lean Infrastructure
```bash
cd infra
terraform init
terraform plan -var="notification_email=you@example.com"
terraform apply -var="notification_email=you@example.com"
```
Keep the Terraform outputs handy—they provide the S3 bucket, Lambda names, and token UI URL.

### 2. Configure Fyers Credentials (SSM Parameter Store)
```bash
# View the parameter prefix
terraform output -raw fyers_parameter_prefix

# Set your Fyers API credentials in SSM Parameter Store
aws ssm put-parameter --name "/stock-pipeline-mvp/fyers/client_id" \
  --value "YOUR_CLIENT_ID" --type "SecureString" --overwrite
aws ssm put-parameter --name "/stock-pipeline-mvp/fyers/app_secret" \
  --value "YOUR_APP_SECRET" --type "SecureString" --overwrite
aws ssm put-parameter --name "/stock-pipeline-mvp/fyers/refresh_token" \
  --value "YOUR_REFRESH_TOKEN" --type "SecureString" --overwrite
# Optional PIN (if required by your Fyers account)
aws ssm put-parameter --name "/stock-pipeline-mvp/fyers/pin" \
  --value "YOUR_PIN" --type "SecureString" --overwrite
```
Access tokens are generated and refreshed automatically by the ingestion Lambda—no daily login required.

### 3. Use the Interactive Token UI (Optional Step)
```
https://{api-id}.execute-api.{region}.amazonaws.com/prod
```
- Paste your refresh token and client details
- Generate a fresh access token
- Lambda stores it in SSM under the configured parameters

---

## 🧰 Repository Structure (Actual MVP)
```
ingestion/                # Ingestion Lambda source
  lambda_ingestion.py      # Main ingestion handler
  requirements.txt         # Python dependencies (requests, pytz, boto3)
etl/
  lightweight_etl.py       # CSV-based ETL (NO Pandas/PyArrow)
  lightweight_requirements.txt
  python_etl/              # Future Parquet-based ETL (not deployed)
    transforms.py
    s3_helpers.py
infra/
  main-mvp.tf              # FREE TIER Terraform stack (Mumbai compatible)
aws-token-generator/
  lambda_function.py       # Token generator backend
  terraform/               # Token generator infra
deployment/
  lambda_package/          # Built Lambda deployment packages
  etl_package/
  token_generator_package/
README.md                  # This file
README-MVP.md              # Detailed MVP guide
```

---

## 🔁 Data Flow (Actual Implementation)
```
Fyers API → Ingestion Lambda (every 5 min during trading hours)
                ↓
          S3: Raw data/Prices/YYYY-MM-DD/raw_file_TIMESTAMP.json
                ↓
          EventBridge schedule (daily at 4:00 PM IST)
                ↓
    Lightweight ETL Lambda (Python stdlib + boto3)
                ↓
          S3: analytics/csv/symbol=SYMBOL/year=YYYY/month=MM/day=DD/data_TIMESTAMP.csv.gz
                ↓
          Query via S3 Select, Athena (manual), or download for local analysis
```

- **Raw zone** (`Raw data/Prices/`) keeps complete JSON for audit/backfill
- **Analytics zone** (`analytics/csv/`) stores compressed CSV files (gzipped)
- **Partitioning** by symbol/year/month/day for efficient queries
- **NO Parquet** - Uses CSV.gz to avoid Pandas/PyArrow Lambda size issues in Mumbai region

---

## 🐍 Lightweight ETL Details

### Key Behaviors
- Uses **pure Python + boto3** (NO Pandas, NO PyArrow) to avoid Lambda package size limits
- Converts raw JSON to **gzipped CSV** files for cost-effective storage and querying
- Runs daily at **4:00 PM IST** (after market close) via EventBridge schedule
- Processes **today's data** (fixed from processing yesterday's data)
- Partitions output by symbol/year/month/day for efficient access
- Idempotent - can be run multiple times safely

### Lambda Handler
```python
# etl/lightweight_etl.py
def lambda_handler(event, context):
    # Automatically processes today's data unless 'date' provided in event
    # Event format: {"date": "2025-10-24"}  (optional)
    ...
```

### Manual Invocation
```bash
# Process specific date
aws lambda invoke \
  --function-name stock-pipeline-mvp-etl \
  --payload '{"date": "2025-10-24"}' \
  response-etl.json
```
```

## 🗂️ Querying Your Data

### Option 1: S3 Select (Free, Simple)
```bash
# Query CSV files directly from S3
aws s3api select-object-content \
    --bucket stock-pipeline-mvp-dev-ohlcv-XXXXX \
    --key "analytics/csv/symbol=RELIANCE/year=2025/month=10/day=24/data_*.csv.gz" \
    --expression "SELECT * FROM s3object s WHERE s.close > 2500" \
    --expression-type 'SQL' \
    --input-serialization '{"CSV": {"FileHeaderInfo": "USE"}, "CompressionType": "GZIP"}' \
    --output-serialization '{"CSV": {}}' \
    output.csv
```

### Option 2: Athena (Optional - pay per query after 10TB scanned)
```sql
-- Create external table for CSV files
CREATE EXTERNAL TABLE IF NOT EXISTS ohlcv_data (
  symbol string,
  symbol_clean string,
  timestamp_unix bigint,
  timestamp_iso string,
  open double,
  high double,
  low double,
  close double,
  volume bigint,
  resolution string,
  fetch_timestamp string,
  year int,
  month int,
  day int,
  hour int,
  processed_at string
)
PARTITIONED BY (
  symbol_partition string,
  year_partition int,
  month_partition int,
  day_partition int
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://your-bucket/analytics/csv/'
TBLPROPERTIES ('skip.header.line.count'='1');

-- Repair partitions
MSCK REPAIR TABLE ohlcv_data;

-- Query example
SELECT symbol_clean, 
       DATE(from_unixtime(timestamp_unix)) AS trading_day,
       MAX(high) AS day_high,
       MIN(low) AS day_low,
       AVG(close) AS avg_close,
       SUM(volume) AS total_volume
FROM ohlcv_data
WHERE year_partition = 2025 AND month_partition = 10
GROUP BY symbol_clean, DATE(from_unixtime(timestamp_unix))
ORDER BY trading_day DESC, symbol_clean;
```

### Option 3: Download and Analyze Locally (Recommended for MVP)
```bash
# Download CSV files
aws s3 cp s3://your-bucket/analytics/csv/ ./local_data/ --recursive

# Decompress and analyze with Python/Excel
gunzip local_data/**/*.csv.gz
```

---

## 🔍 Observability & Operations

### CloudWatch Logs
```bash
# View ingestion Lambda logs
aws logs tail /aws/lambda/stock-pipeline-mvp-ingestion --follow

# View ETL Lambda logs  
aws logs tail /aws/lambda/stock-pipeline-mvp-etl --follow
```

### SNS Email Alerts
- Automatically sent on ingestion success/failure
- ETL processing completion notifications
- Check your email inbox (the one you provided to Terraform)

### Cost Monitoring
- **AWS Budgets**: Alert at 50% and 80% of $5 monthly cap
- **Free Tier Dashboard**: Monitor usage limits
- **Expected Cost**: $0.00/month within free tier

### S3 Data Validation
```bash
# List raw data files
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/Raw\ data/Prices/ --recursive

# List analytics CSV files
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/analytics/csv/ --recursive

# Download a sample file
aws s3 cp "s3://$(terraform output -raw s3_bucket_name)/analytics/csv/symbol=RELIANCE/year=2025/month=10/day=24/data_*.csv.gz" sample.csv.gz
gunzip sample.csv.gz
cat sample.csv
```

### Manual Lambda Test
```bash
# Test ingestion Lambda
aws lambda invoke \
  --function-name $(terraform output -raw lambda_function_name) \
  --payload '{}' \
  response.json
cat response.json

# Test ETL Lambda for today
aws lambda invoke \
  --function-name $(terraform output -raw etl_lambda_function_name) \
  --payload '{}' \
  response-etl.json
cat response-etl.json

# Test ETL Lambda for specific date
aws lambda invoke \
  --function-name stock-pipeline-mvp-etl \
  --payload '{"date": "2025-10-24"}' \
  response-etl.json
```

---

## 🛠️ Local Development & Testing

### Test Ingestion Locally
```bash
cd ingestion
python lambda_ingestion.py  # Requires AWS credentials and SSM parameters configured
```

### Test ETL Locally
```bash
cd etl
python lightweight_etl.py  # Can test transformation logic
```

### View Terraform Outputs
```bash
cd infra
terraform output  # Show all outputs
terraform output s3_bucket_name  # Specific output
terraform output -json  # JSON format for scripting
```

---

## 📈 Current Features & Limitations

### ✅ What's Implemented (MVP)
- ✅ **Automated data ingestion** every 5 minutes during trading hours (9:15 AM - 3:30 PM IST)
- ✅ **Daily ETL processing** at 4:00 PM IST (processes today's data)
- ✅ **Automatic token refresh** - no manual login needed
- ✅ **Interactive token generator UI** for initial setup
- ✅ **Email notifications** for all pipeline events
- ✅ **SSM Parameter Store** for secure credential management
- ✅ **S3 data lake** with partitioned storage
- ✅ **CloudWatch logging** and monitoring
- ✅ **Cost alerts** via AWS Budgets
- ✅ **100% Free Tier compatible** (Mumbai region)

### ⚠️ Not Implemented (Commented Out)
- ❌ **Analytics Lambda** (Pandas too large for Mumbai Lambda without layers)
- ❌ **Parquet format** (using CSV.gz instead to avoid Pandas/PyArrow)
- ❌ **RDS PostgreSQL** (not needed for MVP, uses S3)
- ❌ **ECS Fargate** (Lambda sufficient for MVP)
- ❌ **AWS Glue** (using lightweight Python ETL instead)
- ❌ **Real-time streaming** (batch processing only)

### 🔮 Future Enhancements (Optional)
- Parquet-based ETL when Lambda Layers available in Mumbai
- Step Functions for workflow orchestration  
- AWS Batch for bulk backfills
- Data quality checks with CloudWatch metrics
- Glue Crawler for automatic Athena partition discovery
- API Gateway for programmatic data access

---

## 🙌 Project Info

### Architecture Philosophy
- **Free Tier First**: All services chosen to stay within AWS free tier limits
- **Mumbai Region Compatible**: No Lambda Layers (avoiding Pandas/PyArrow size issues)
- **Lightweight & Fast**: Pure Python + boto3, minimal dependencies
- **Automation**: Fully automated data collection and processing
- **Security**: Credentials in SSM Parameter Store, no hardcoded secrets

### What Makes This MVP Special
- ✅ Solves the "Pandas too large for Lambda in Mumbai" problem
- ✅ Automatic token refresh (no daily manual login)
- ✅ Interactive web UI for token generation
- ✅ Costs $0.00/month within free tier limits
- ✅ Production-ready monitoring and alerting
- ✅ Clean separation of raw and processed data

### Documentation
- `README.md` - This file (main documentation)
- `README-MVP.md` - Detailed MVP deployment guide
- `TOKEN_MANAGEMENT_GUIDE.md` - Token generation instructions
- `AWS_TOKEN_GENERATOR_GUIDE.md` - Token UI usage
- `FREE_TIER_ALTERNATIVES.md` - Cost optimization tips
- `ETL_DEPLOYMENT_GUIDE.md` - ETL detailed documentation

---

**Happy building!** 🏗️📊 For questions or issues, check CloudWatch logs first!
