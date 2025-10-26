# FREE-TIER AWS ALTERNATIVES TO ATHENA

**Context:** You're correct that Athena has NO free tier - it's pure pay-per-query ($5/TB scanned). Here are completely FREE alternatives for querying your 500-stock OHLCV data.

---

## 📊 YOUR DATA PROFILE
- **Records/month:** 1,440,000 (500 symbols × 96 intervals/day × 30 days)
- **Storage/month:** 23 MB (CSV+GZIP)
- **Query pattern:** Analytics queries (aggregations, filtering by symbol/date)

---

## 🆓 OPTION 1: AWS LAMBDA + S3 SELECT (RECOMMENDED FOR FREE)

### What is it?
Lambda function queries CSV files directly using S3 Select API (SQL-like filtering on S3 objects).

### FREE TIER (Permanent)
- **Lambda Requests:** 1M requests/month FREE (forever)
- **Lambda Compute:** 400,000 GB-seconds/month FREE (forever)
- **S3 Select:** FREE for scanned data < 10 GB/month
- **S3 Storage:** 5 GB FREE (first 12 months)

### Cost Calculation
```
50 queries/day × 30 days = 1,500 queries/month
Lambda: 1,500 / 1,000,000 = 0.15% used ✅
Compute: 768 GB-sec / 400,000 = 0.19% used ✅
Monthly cost: $0.00
```

### Sample Lambda Code
```python
import boto3
import json

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    
    # Query CSV using S3 Select
    resp = s3.select_object_content(
        Bucket='your-bucket',
        Key=f'analytics/csv/symbol={event["symbol"]}/year=2025/month=10/day=07/data.csv.gz',
        Expression='SELECT * FROM s3object s WHERE s.close > 100',
        ExpressionType='SQL',
        InputSerialization={'CSV': {'FileHeaderInfo': 'USE'}, 'CompressionType': 'GZIP'},
        OutputSerialization={'JSON': {}}
    )
    
    # Process results
    for record in resp['Payload']:
        if 'Records' in record:
            return json.loads(record['Records']['Payload'].decode())
```

### Pros
✅ **Completely FREE** (within generous limits)  
✅ **Serverless** - No infrastructure to manage  
✅ **Fast** - 2-5 second query response  
✅ **Can build REST API** - Add API Gateway for web access  

### Cons
❌ **Limited SQL** - No complex joins/aggregations (filtering only)  
❌ **Coding required** - Must write Lambda for each query type  
❌ **No visual editor** - Code-based queries only  

### Best For
Simple filtering queries, API-driven access, completely free solution.

---

## 🆓 OPTION 2: AMAZON DYNAMODB

### What is it?
NoSQL database optimized for key-value lookups (e.g., get OHLCV for RELIANCE on 2025-10-07).

### FREE TIER (Permanent)
- **Storage:** 25 GB FREE (forever)
- **Reads:** 25 RCU = 518 million reads/month FREE
- **Writes:** 25 WCU = 64 million writes/month FREE

### Cost Calculation
```
Storage: 0.023 GB / 25 GB = 0.09% used ✅
Reads: 150,000/month / 518M = 0.03% used ✅
Writes: 1,440,000/month / 64M = 2.25% used ✅
Monthly cost: $0.00
```

### Sample Query Code
```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ohlcv_data')

# Query by partition key (symbol + date)
response = table.query(
    KeyConditionExpression='symbol = :s AND date = :d',
    ExpressionAttributeValues={
        ':s': 'RELIANCE',
        ':d': '2025-10-07'
    }
)

for item in response['Items']:
    print(f"{item['timestamp']}: Open={item['open']}, Close={item['close']}")
```

### Pros
✅ **Completely FREE** (massive limits)  
✅ **Ultra-fast** - Single-item queries <10ms  
✅ **No scanning costs** - Fixed capacity model  
✅ **Good for time-series** - Perfect for symbol+date lookups  

### Cons
❌ **Poor for analytics** - No native GROUP BY, AVG, SUM (must code)  
❌ **Must query by key** - Partition key required (symbol+date)  
❌ **1 MB query limit** - Can't scan large datasets  
❌ **Not SQL** - Different query model (NoSQL)  

### Best For
Real-time lookups by symbol+date, not complex analytics.

---

## 🆓 OPTION 3: S3 + PANDAS IN LAMBDA (BEST FREE OPTION!)

### What is it?
Lambda reads CSV from S3 and processes with Pandas for full analytics capabilities.

### FREE TIER (Permanent)
- **Lambda:** 1M requests + 400K GB-sec/month FREE
- **S3 Storage:** 5 GB FREE (first 12 months)
- **S3 GET Requests:** 20,000/month FREE

### Cost Calculation
```
Lambda (1 GB memory, 5 sec/query): 7,500 GB-sec / 400,000 = 1.9% used ✅
S3 GET requests: 1,500 / 20,000 = 7.5% used ✅
Monthly cost: $0.00
```

### Sample Lambda Code
```python
import boto3
import pandas as pd
import io

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    
    # Read CSV from S3
    obj = s3.get_object(
        Bucket='your-bucket',
        Key=f'analytics/csv/symbol={event["symbol"]}/year=2025/month=10/day=07/data.csv.gz'
    )
    
    # Load into Pandas
    df = pd.read_csv(io.BytesIO(obj['Body'].read()), compression='gzip')
    
    # Full analytics!
    result = {
        'avg_close': float(df['close'].mean()),
        'max_high': float(df['high'].max()),
        'min_low': float(df['low'].min()),
        'total_volume': int(df['volume'].sum()),
        'price_change': float(df['close'].iloc[-1] - df['open'].iloc[0])
    }
    
    return result
```

### Deployment
```powershell
# Create deployment package with Pandas
cd deployment
pip install pandas -t lambda_analytics/
cp ../examples/analytics_lambda.py lambda_analytics/lambda_function.py
cd lambda_analytics
zip -r ../lambda_analytics.zip .

# Deploy via Terraform (add to main-mvp.tf)
```

### Pros
✅ **Completely FREE** (forever)  
✅ **Full Python/Pandas** - All analytics capabilities  
✅ **Complex analytics** - GROUP BY, aggregations, calculations  
✅ **Flexible** - Easy to add new query types  
✅ **Can cache results** - Store in Lambda /tmp  

### Cons
❌ **Slower** - 5-10 seconds per query (vs Athena 2-3s)  
❌ **Coding required** - Write Lambda for each query  
❌ **15-min timeout** - Can't scan massive datasets  
❌ **10 GB ephemeral storage** - Limited temp space  

### Best For
**Custom analytics, periodic reports, flexible querying - BEST FREE OPTION!**

---

## 💰 OPTION 4: RDS FREE TIER (TEMPORARY)

### What is it?
Traditional SQL database (PostgreSQL/MySQL).

### FREE TIER (12 months for NEW AWS accounts only)
- **Compute:** 750 hours/month db.t3.micro (12 months)
- **Storage:** 20 GB SSD (12 months)
- **Backups:** 20 GB backup storage (12 months)

### Cost
```
Months 1-12: $0.00 (FREE TIER)
After 12 months: $12.41/month ($149/year)
```

### Pros
✅ **Full SQL** - Complex queries, joins, aggregations  
✅ **FREE for 12 months** (new accounts)  
✅ **Familiar tools** - pgAdmin, MySQL Workbench  
✅ **ACID transactions**  

### Cons
❌ **Only 12 months FREE** (new accounts only)  
❌ **$12.41/month after** - Ongoing costs  
❌ **Database management** - Patching, backups required  
❌ **Runs 24/7** - Idle costs even when not querying  

### Best For
12-month temporary projects, complex SQL analytics (not long-term).

---

## 📈 OPTION 5: ATHENA (CURRENT PLAN - NEARLY FREE)

### Cost
```
With partitioning: $0.02/month (~$0.24/year)
Without partitioning: $0.03/month
```

### Pros
✅ **SQL queries** - Standard SQL syntax  
✅ **Visual editor** - AWS Console query interface  
✅ **Built for analytics** - Optimized for large datasets  
✅ **No coding** - Write SQL directly  
✅ **Partition pruning** - Query only needed data  

### Cons
❌ **Not free tier** - Pay-per-query (but nearly free)  
❌ **$5/TB scanned** - Costs scale with data scanned  

### Best For
**Professional analytics, SQL queries, minimal maintenance - BEST VALUE!**

---

## 🏆 FINAL RECOMMENDATION MATRIX

| Option | Monthly Cost | Free Forever? | SQL Support | Best Use Case | Rating |
|--------|-------------|---------------|-------------|---------------|--------|
| **S3 + Pandas Lambda** | **$0.00** | ✅ Yes | Python code | Custom analytics | ⭐⭐⭐⭐⭐ |
| **Lambda + S3 Select** | $0.00 | ✅ Yes | Basic SQL | Simple filtering | ⭐⭐⭐⭐ |
| **DynamoDB** | $0.00 | ✅ Yes | NoSQL | Symbol+date lookups | ⭐⭐⭐ |
| **Athena** | **$0.02** | ❌ No | Full SQL | Advanced analytics | ⭐⭐⭐⭐⭐ |
| **RDS Free Tier** | $0.00 (12mo) | ❌ No | Full SQL | Temporary projects | ⭐⭐ |

---

## ✅ TOP 2 RECOMMENDATIONS

### 🥇 **RECOMMENDED: S3 + PANDAS IN LAMBDA**

**Why:** 100% FREE forever, full analytics capabilities, serverless.

**Setup Steps:**
1. Keep CSV files in S3 (already doing this ✅)
2. Create Lambda function with Pandas layer
3. Write query functions for common analytics
4. Optional: Add API Gateway for REST API

**Example Use Cases:**
```python
# Daily summary for all symbols
GET /analytics/daily-summary?date=2025-10-07

# Symbol performance
GET /analytics/symbol/RELIANCE?from=2025-10-01&to=2025-10-07

# Top gainers/losers
GET /analytics/top-movers?date=2025-10-07&limit=10
```

**Cost:** $0.00/month (within free tier limits)

---

### 🥈 **EASIEST: STICK WITH ATHENA**

**Why:** SQL queries, visual editor, no coding, nearly free ($0.02/month).

**Cost Breakdown:**
- 50 queries/day with partitioning = $0.02/month
- 620x cheaper than RDS ($0.02 vs $12.41)
- 99.9% cheaper than unpartitioned queries

**Savings:** $12.39/month vs RDS = **$149/year saved!**

---

## 🎯 DECISION GUIDE

**Choose S3 + Pandas Lambda if:**
- You want **100% FREE** (no costs ever)
- You're comfortable writing Python code
- You need custom analytics logic
- Query speed 5-10 seconds is acceptable

**Choose Athena if:**
- You want **easiest solution** (SQL only, no coding)
- $0.02/month is acceptable (nearly free)
- You want visual query editor
- You need fast queries (2-3 seconds)

**Avoid RDS because:**
- ❌ $12.41/month after 12 months
- ❌ Only free for new AWS accounts
- ❌ Requires database management
- ❌ 620x more expensive than Athena

---

## 📝 MIGRATION PATH (If choosing Lambda)

```powershell
# 1. Create analytics Lambda function
cd d:\Price Feed Parser\examples
# Create analytics_lambda.py (Pandas-based queries)

# 2. Deploy Lambda
cd ..\deployment
# Package with Pandas layer
# Deploy via Terraform

# 3. Test queries
aws lambda invoke --function-name stock-analytics \
  --payload '{"symbol":"RELIANCE","date":"2025-10-07"}' \
  response.json

# 4. Optional: Add API Gateway
# Expose Lambda as REST API
```

**Estimated effort:** 2-3 hours (vs 2 minutes for Athena setup)

---

## 💡 FINAL ANSWER

For your 500-stock analytics pipeline:

### **IF you want COMPLETELY FREE:**
→ **Use S3 + Pandas in Lambda**  
→ $0.00/month, requires Python coding (2-3 hours setup)

### **IF you want EASIEST + NEARLY FREE:**
→ **Use Athena with partitioning** (current plan)  
→ $0.02/month, SQL queries, no coding (2 minutes setup)

### **Both are FAR better than RDS ($12.41/month)!**

**My recommendation:** Start with **Athena** (fastest to deploy), migrate to **Lambda+Pandas** later if you want to eliminate even the $0.02/month cost.

---

## 📚 NEXT STEPS

**Ready to proceed with Athena?**
```powershell
cd d:\Price Feed Parser\scripts
.\setup-athena-table.ps1
```

**Want to build Lambda+Pandas instead?**
Let me know and I'll create the complete implementation!
