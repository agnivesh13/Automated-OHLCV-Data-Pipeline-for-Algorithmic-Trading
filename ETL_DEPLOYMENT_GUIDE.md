# Quick Deployment Guide - Lightweight ETL Lambda

## 🚀 Deploy in 5 Minutes

### Prerequisites
- ✅ Terraform installed
- ✅ AWS CLI configured
- ✅ Existing infrastructure deployed

---

## Step 1: Validate Terraform Configuration

```powershell
cd "d:\Price Feed Parser\infra"
terraform validate
```

**Expected**: `Success! The configuration is valid.`

---

## Step 2: Review Changes

```powershell
terraform plan -var="notification_email=your@email.com"
```

**Expected changes**:
- ✅ Add `aws_lambda_function.lightweight_etl`
- ✅ Add `aws_cloudwatch_log_group.etl_logs`
- ✅ Add `aws_cloudwatch_event_rule.etl_schedule`
- ✅ Add `aws_cloudwatch_event_target.etl_target`
- ✅ Add `aws_lambda_permission.allow_eventbridge_etl`
- ✅ Modify outputs (non-destructive)

**Total**: ~7 resources to add, 0 to destroy

---

## Step 3: Deploy

```powershell
terraform apply -var="notification_email=your@email.com"
```

Type `yes` when prompted.

**Deployment time**: ~2-3 minutes

---

## Step 4: Verify Deployment

```powershell
# Check Lambda functions
terraform output -json | ConvertFrom-Json | Select-Object -ExpandProperty deployment_summary

# Or manually verify
aws lambda list-functions --query 'Functions[?contains(FunctionName, `etl`)].{Name:FunctionName,Runtime:Runtime,Size:CodeSize}'
```

**Expected output**:
```json
{
  "Name": "stock-pipeline-mvp-etl",
  "Runtime": "python3.11",
  "Size": 1024  # < 50 KB!
}
```

---

## Step 5: Test ETL Manually (Optional)

```powershell
# Run ETL for October 1st data
aws lambda invoke `
  --function-name stock-pipeline-mvp-etl `
  --payload '{"date": "2025-10-01"}' `
  response.json

# Check result
Get-Content response.json | ConvertFrom-Json
```

**Expected response**:
```json
{
  "statusCode": 200,
  "body": "{\"processed_files\": 96, \"total_records\": 2880, \"symbols_processed\": 30}"
}
```

---

## Step 6: Check S3 Output

```powershell
$bucket = terraform output -raw s3_bucket_name
aws s3 ls "s3://$bucket/analytics/csv/" --recursive --human-readable | Select-Object -First 20
```

**Expected structure**:
```
analytics/csv/
  symbol=RELIANCE/year=2025/month=10/day=01/data_20251007T103000Z.csv.gz
  symbol=TCS/year=2025/month=10/day=01/data_20251007T103000Z.csv.gz
  symbol=INFY/year=2025/month=10/day=01/data_20251007T103000Z.csv.gz
```

---

## Step 7: Create Athena Table

1. Open **Athena Console**: https://console.aws.amazon.com/athena/
2. Create/select database (e.g., `stock_analytics`)
3. Copy SQL from `sql/athena_lightweight_csv.sql`
4. Replace `YOUR_BUCKET_NAME` with actual bucket name:

```powershell
$bucket = terraform output -raw s3_bucket_name
Write-Host "Replace YOUR_BUCKET_NAME with: $bucket"
```

5. Run the CREATE TABLE statement

---

## Step 8: Query Your Data

```sql
-- Test query
SELECT 
  symbol_clean,
  timestamp_iso,
  close,
  volume
FROM ohlcv_csv
WHERE year = 2025 
  AND month = 10 
  AND day = 1
  AND symbol = 'RELIANCE'
ORDER BY timestamp_iso
LIMIT 10;
```

**Expected**: ~96 rows of RELIANCE data for Oct 1st

---

## 🎯 What Just Happened?

✅ **ETL Lambda deployed** - Lightweight, no external dependencies  
✅ **Scheduled daily** - Runs at 4 PM IST after market close  
✅ **Processing raw JSON** → **CSV + GZIP**  
✅ **Partitioned by symbol** - Efficient Athena queries  
✅ **Zero cost** - 100% Free Tier compatible  

---

## 📊 Monitoring

### CloudWatch Logs
```powershell
terraform output -raw etl_cloudwatch_logs_url
# Open in browser
```

### Check ETL Schedule
```powershell
aws events describe-rule --name stock-pipeline-mvp-etl-schedule
```

**Schedule**: `cron(30 10 ? * MON-FRI *)` = Daily 10:30 AM UTC (4:00 PM IST)

---

## 🔄 Manual ETL Runs

### Process specific date
```powershell
aws lambda invoke `
  --function-name stock-pipeline-mvp-etl `
  --payload '{"date": "2025-10-05"}' `
  response.json
```

### Process yesterday (default)
```powershell
aws lambda invoke `
  --function-name stock-pipeline-mvp-etl `
  --payload '{}' `
  response.json
```

---

## 🐛 Troubleshooting

### Issue: No CSV files created
**Check**:
```powershell
# 1. Verify raw data exists
$bucket = terraform output -raw s3_bucket_name
aws s3 ls "s3://$bucket/Raw data/Prices/2025-10-01/" --recursive

# 2. Check Lambda logs
aws logs tail /aws/lambda/stock-pipeline-mvp-etl --follow
```

### Issue: Athena query fails
**Fix**: Add partitions manually
```sql
MSCK REPAIR TABLE ohlcv_csv;
```

### Issue: Lambda timeout
**Increase timeout** in `main-mvp.tf`:
```hcl
resource "aws_lambda_function" "lightweight_etl" {
  timeout = 900  # 15 minutes instead of 10
}
```

---

## 📈 Next Steps

1. **Wait for automatic run** - Tomorrow at 4 PM IST
2. **Check SNS email** - Success notification
3. **Run Athena queries** - Analyze your data
4. **Set up dashboards** (optional) - QuickSight or custom

---

## 🎉 Success Criteria

✅ ETL Lambda deployed  
✅ EventBridge schedule active  
✅ CSV files in S3 analytics folder  
✅ Athena table created  
✅ Sample query returns data  
✅ SNS notification received  

**All green?** → You're done! 🚀

---

## 💰 Cost Monitoring

```powershell
# Check current month costs
aws ce get-cost-and-usage `
  --time-period Start=2025-10-01,End=2025-10-07 `
  --granularity DAILY `
  --metrics BlendedCost `
  --group-by Type=SERVICE
```

**Expected**: $0.00 (all within Free Tier)

---

## 📞 Support

- **Terraform docs**: `terraform plan -help`
- **Lambda logs**: CloudWatch console
- **S3 browser**: `terraform output -raw s3_console_url`
- **Cost dashboard**: AWS Billing Console

---

**Deployment Status**: Ready to deploy! ✅  
**Estimated Time**: 5 minutes  
**Risk Level**: Very Low  
**Rollback**: `terraform destroy` (if needed)
