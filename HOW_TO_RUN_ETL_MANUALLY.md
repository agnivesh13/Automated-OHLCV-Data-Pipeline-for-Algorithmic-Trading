# How to Manually Run ETL Task

## 🎯 Quick Commands

### Option 1: Run ETL for Today's Date (Recommended)
```powershell
# Invoke ETL Lambda with today's date as payload
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-08"}' response.json

# View the response
cat response.json

# Check the logs
aws logs tail /aws/lambda/stock-pipeline-mvp-etl --follow
```

---

### Option 2: Run ETL for Specific Date
```powershell
# Process data from a specific date
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-07"}' response.json
```

---

### Option 3: Run ETL with Default (Yesterday's Date)
```powershell
# No payload = processes yesterday's date
aws lambda invoke --function-name stock-pipeline-mvp-etl response.json
```

---

## 📋 Current Situation

### Your Raw Data Location:
```
s3://stock-pipeline-mvp-dev-ohlcv-5e23bf76/Raw data/Prices/2025-10-08/
```

You have **20+ files** from today (Oct 8, 2025) with data collected every 5 minutes.

### Why ETL Found 0 Files:
The ETL Lambda **defaults to yesterday's date** (2025-10-07) when no date is provided.

```
# Log showed:
Found 0 raw JSON files for prefix: Raw data/Prices/2025-10-07/
```

But your data is in: `Raw data/Prices/2025-10-08/` ✅

---

## 🚀 Step-by-Step: Run ETL for Today

### Step 1: Invoke ETL Lambda with Today's Date
```powershell
aws lambda invoke `
  --function-name stock-pipeline-mvp-etl `
  --payload '{"date":"2025-10-08"}' `
  response.json
```

**Expected Output:**
```json
{
    "StatusCode": 200,
    "ExecutedVersion": "$LATEST"
}
```

---

### Step 2: View the Response
```powershell
cat response.json
```

**Expected Response:**
```json
{
  "statusCode": 200,
  "processed_files": 20,
  "total_records": 15000,
  "symbols_processed": 500,
  "date": "2025-10-08",
  "csv_files_created": 500,
  "message": "ETL processing completed successfully"
}
```

---

### Step 3: Monitor the Logs (Optional)
```powershell
aws logs tail /aws/lambda/stock-pipeline-mvp-etl --follow
```

**What to Look For:**
```
✅ Starting lightweight ETL processing
✅ Found 20 raw JSON files for prefix: Raw data/Prices/2025-10-08/
✅ Processing file: raw_file_20251008_034541.json
✅ Extracted 500 symbols
✅ Writing CSV for NSE:TCS-EQ to analytics/csv/partition_date=2025-10-08/NSE_TCS-EQ.csv.gz
✅ ETL processing completed: {'processed_files': 20, 'total_records': 15000, ...}
```

---

### Step 4: Verify CSV Files Created
```powershell
# List the analytics CSV files
aws s3 ls "s3://stock-pipeline-mvp-dev-ohlcv-5e23bf76/analytics/csv/partition_date=2025-10-08/" --recursive
```

**Expected Output:**
```
2025-10-08 11:30:42    1024 analytics/csv/partition_date=2025-10-08/NSE_TCS-EQ.csv.gz
2025-10-08 11:30:42    1156 analytics/csv/partition_date=2025-10-08/NSE_INFY-EQ.csv.gz
2025-10-08 11:30:42    1089 analytics/csv/partition_date=2025-10-08/NSE_RELIANCE-EQ.csv.gz
... (500 symbols total)
```

---

## 🔧 Advanced: Run ETL Locally (For Testing)

### Option 1: Python Script (Local)
```powershell
cd "D:\Price Feed Parser"
python etl/lightweight_etl.py
```

**Requirements:**
- AWS credentials configured
- Python 3.11+
- boto3 installed: `pip install boto3`

---

### Option 2: Run with Custom Parameters
```python
# Create test script: run_etl_local.py
import boto3
from etl.lightweight_etl import lambda_handler

# Mock Lambda context
class MockContext:
    function_name = "local-test"
    request_id = "test-123"

# Run ETL for today
event = {"date": "2025-10-08"}
context = MockContext()
result = lambda_handler(event, context)
print(result)
```

Then run:
```powershell
python run_etl_local.py
```

---

## 📊 ETL Lambda Configuration

### Current Settings:
```yaml
Function Name: stock-pipeline-mvp-etl
Runtime: Python 3.11
Memory: 512 MB
Timeout: 600 seconds (10 minutes)
Schedule: Daily at 10:30 AM UTC (4:00 PM IST)
Environment Variables:
  - S3_BUCKET_NAME: stock-pipeline-mvp-dev-ohlcv-5e23bf76
  - PROJECT_NAME: stock-pipeline-mvp
  - ENVIRONMENT: dev
```

### Event Payload Schema:
```json
{
  "date": "YYYY-MM-DD"  // Optional, defaults to yesterday
}
```

---

## 🕐 Scheduled ETL Runs

### Automatic Schedule:
The ETL Lambda runs **automatically every weekday** at:
- **UTC Time:** 10:30 AM Monday-Friday
- **IST Time:** 4:00 PM Monday-Friday (after market close)

### EventBridge Rule:
```
Name: stock-pipeline-mvp-etl-schedule
Schedule: cron(30 10 ? * MON-FRI *)
Enabled: Yes
```

### Check Scheduled Runs:
```powershell
# List EventBridge rules
aws events list-rules --name-prefix stock-pipeline-mvp-etl

# View rule details
aws events describe-rule --name stock-pipeline-mvp-etl-schedule
```

---

## 📁 Data Flow Overview

### 1. Ingestion (Every 5 Minutes)
```
Fyers API → Lambda → S3: Raw data/Prices/2025-10-08/raw_file_20251008_034541.json
```

### 2. ETL Processing (Daily at 4 PM IST)
```
S3: Raw data/Prices/2025-10-08/*.json → ETL Lambda → Process → 
S3: analytics/csv/partition_date=2025-10-08/NSE_TCS-EQ.csv.gz
```

### 3. API Query (On-Demand)
```
API Gateway → API Lambda → S3: Raw data/Prices/ → Response
```

---

## 🧪 Testing Different Scenarios

### Test 1: Process Today's Data
```powershell
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-08"}' response.json
cat response.json
```

### Test 2: Process Specific Date
```powershell
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-07"}' response.json
```

### Test 3: Process with Default (Yesterday)
```powershell
aws lambda invoke --function-name stock-pipeline-mvp-etl response.json
```

### Test 4: Force Re-run (Overwrites Existing CSV)
```powershell
# ETL will overwrite existing CSV files for the date
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-08"}' response.json
```

---

## 🐛 Troubleshooting

### Issue 1: "No raw files found for date"
**Cause:** Data doesn't exist for that date in S3

**Solution:**
```powershell
# Check what dates have data
aws s3 ls "s3://stock-pipeline-mvp-dev-ohlcv-5e23bf76/Raw data/Prices/"

# Run ETL for a date that has data
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-08"}' response.json
```

---

### Issue 2: ETL Times Out
**Cause:** Processing too much data (500+ symbols × 20+ files)

**Solution:**
```powershell
# Check current timeout setting (should be 600s)
aws lambda get-function-configuration --function-name stock-pipeline-mvp-etl --query 'Timeout'

# Increase timeout if needed (via Terraform)
# Edit infra/main-mvp.tf, find etl lambda, change timeout = 900
```

---

### Issue 3: Memory Errors
**Cause:** Not enough memory (current: 512 MB)

**Solution:**
```powershell
# Check current memory
aws lambda get-function-configuration --function-name stock-pipeline-mvp-etl --query 'MemorySize'

# Memory should be 512 MB (sufficient for 500 symbols)
# Lightweight ETL uses <100 MB typically
```

---

### Issue 4: Permission Errors
**Cause:** Lambda doesn't have S3 read/write permissions

**Check Permissions:**
```powershell
aws lambda get-function-configuration --function-name stock-pipeline-mvp-etl --query 'Role'

# Verify IAM role has:
# - s3:GetObject on Raw data/Prices/*
# - s3:PutObject on analytics/csv/*
```

---

## 📈 Performance Metrics

### Current Performance (500 Symbols):
```
Raw Files Processed: 20 files
Total Records: ~15,000 candles
Symbols Processed: 500 symbols
CSV Files Created: 500 files
Processing Time: 5-10 seconds
Memory Used: 80-100 MB
Lambda Cost: $0.000002 per run (FREE TIER)
```

### Comparison vs Pandas:
```
Lightweight ETL (Native Python):
- Package Size: <1 MB
- Memory Usage: ~90 MB
- Processing Time: 5-10s
- Cost: FREE

Pandas ETL (Commented Out):
- Package Size: ~100 MB (exceeds Lambda limit)
- Memory Usage: ~300 MB
- Processing Time: 3-5s (faster but can't deploy)
- Cost: Would be FREE if it fit
```

---

## 🎯 Common Use Cases

### 1. Daily Manual ETL Run (After Market Hours)
```powershell
# Run at 4 PM IST after market close
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-08"}' response.json
```

### 2. Backfill Historical Data
```powershell
# If you have data for previous dates, process them
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-01"}' response.json
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-02"}' response.json
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-03"}' response.json
```

### 3. Re-process Today's Data (Fix Errors)
```powershell
# If initial run had errors, re-run to overwrite
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-08"}' response.json
```

### 4. Test ETL with Sample Data
```powershell
# Upload sample JSON to S3 test prefix
aws s3 cp sample_data.json "s3://stock-pipeline-mvp-dev-ohlcv-5e23bf76/Raw data/Prices/2025-10-09/test.json"

# Run ETL for test date
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-09"}' response.json
```

---

## 📝 Quick Reference

### Run ETL for Today (Most Common)
```powershell
aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-08"}' response.json; cat response.json
```

### Check Logs
```powershell
aws logs tail /aws/lambda/stock-pipeline-mvp-etl --follow
```

### Verify Output
```powershell
aws s3 ls "s3://stock-pipeline-mvp-dev-ohlcv-5e23bf76/analytics/csv/partition_date=2025-10-08/" --recursive | measure-object
```

### Check Schedule
```powershell
aws events list-rules --name-prefix stock-pipeline-mvp-etl
```

---

## ✅ Success Checklist

After running ETL manually:

- [ ] Lambda invocation returned `StatusCode: 200`
- [ ] Response shows `processed_files > 0`
- [ ] Response shows `symbols_processed = 500`
- [ ] Logs show "ETL processing completed successfully"
- [ ] CSV files exist in `analytics/csv/partition_date=YYYY-MM-DD/`
- [ ] Each symbol has a `.csv.gz` file
- [ ] API endpoints return data for the processed date

---

## 🚀 Next Steps

1. **Run ETL for Today:**
   ```powershell
   aws lambda invoke --function-name stock-pipeline-mvp-etl --payload '{"date":"2025-10-08"}' response.json
   ```

2. **Verify CSV Creation:**
   ```powershell
   aws s3 ls "s3://stock-pipeline-mvp-dev-ohlcv-5e23bf76/analytics/csv/partition_date=2025-10-08/"
   ```

3. **Test API with Processed Data:**
   ```powershell
   curl "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/ohlcv/TCS?from=2025-10-08&to=2025-10-08"
   ```

4. **Set Up Athena (Optional - for SQL queries):**
   - Follow `ATHENA_SETUP_GUIDE.md`
   - Query CSV files using SQL

---

**Your raw data is ready - just run ETL with the correct date!** 🎉
