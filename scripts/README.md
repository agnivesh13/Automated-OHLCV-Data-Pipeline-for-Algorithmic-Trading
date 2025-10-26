# Stock Data Fetcher - MVP Setup Guide

## Prerequisites
```bash
pip install boto3 pandas flask
```

## Option 1: Command Line Tool
```bash
# List all available data files
python scripts/fetch_data.py --list

# Get latest data summary
python scripts/fetch_data.py

# Get data for specific date
python scripts/fetch_data.py --date 2025-08-29

# Get data for specific symbol
python scripts/fetch_data.py --symbol RELIANCE
```

## Option 2: Web Dashboard
```bash
# Start the web dashboard
python scripts/dashboard.py

# Then open: http://localhost:5000
```

## Option 3: Direct AWS CLI
```bash
# Get your bucket name
aws s3 ls | grep ohlcv

# List all data files
aws s3 ls s3://your-bucket-name/ohlcv/ --recursive

# Download latest file
aws s3 cp s3://your-bucket-name/ohlcv/2025/08/29/filename.json ./data.json

# View the data
cat data.json | jq .
```

## Option 4: Enable Athena (Advanced)
If you want SQL querying capabilities, uncomment the Athena resources in main-mvp.tf:

```terraform
# Uncomment the Athena section in main-mvp.tf
resource "aws_athena_workgroup" "ohlcv" { ... }
resource "aws_s3_bucket" "athena_results" { ... }
```

Then create tables:
```sql
CREATE EXTERNAL TABLE ohlcv_data (
    symbol string,
    open double,
    high double,
    low double,
    close double,
    volume bigint,
    timestamp string
)
STORED AS JSON
LOCATION 's3://your-bucket-name/ohlcv/'
```

## Troubleshooting

### No Data Available?
1. Check if Lambda function has run: CloudWatch Logs
2. Verify Fyers API credentials in SSM Parameter Store
3. Check S3 bucket for files: `aws s3 ls s3://bucket-name/`

### Access Denied?
1. Ensure AWS credentials are configured: `aws configure`
2. Check IAM permissions for S3 access
3. Verify bucket name is correct

### Want Real-time Updates?
1. Set EventBridge schedule to run more frequently
2. Enable SNS notifications for new data
3. Use WebSocket for live dashboard updates

## Next Steps

1. **Configure API Credentials**: Update SSM parameters with real Fyers API keys
2. **Test Data Flow**: Manually trigger Lambda or wait for scheduled run
3. **Set up Monitoring**: Check CloudWatch logs and set up alerts
4. **Add Analytics**: Uncomment Athena resources for SQL queries
5. **Build Features**: Add charts, alerts, portfolio tracking, etc.
