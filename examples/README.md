# Stock Data API - Integration Examples

This folder contains examples and tools for other teams to integrate with the Stock Price Feed Pipeline.

## 📁 Files Overview

### Core Client Library
- **`stock_client.py`** - Main Python client library for accessing stock data
- **`quick_start.py`** - Quick start example showing common usage patterns

### Team Setup Tools
- **`setup_team_access.sh`** - Bash script to create team-specific access configuration
- **`setup_team_access.ps1`** - PowerShell script for Windows teams

### Configuration Files
- **`../api_config.json`** - API configuration and metadata
- **`../API_INTEGRATION_GUIDE.md`** - Comprehensive integration documentation

## 🚀 Quick Start for Teams

### 1. Set Up Access (Linux/Mac)
```bash
# Create team configuration
./setup_team_access.sh trading-team trader@company.com

# Install dependencies
pip install -r requirements_trading-team.txt

# Configure AWS credentials
aws configure
# Set region to: ap-south-1

# Test access
export TEAM_NAME=trading-team
python sample_trading-team.py
```

### 2. Set Up Access (Windows)
```powershell
# Create team configuration
.\setup_team_access.ps1 -TeamName "trading-team" -Email "trader@company.com"

# Install dependencies
pip install -r requirements_trading-team.txt

# Configure AWS credentials
aws configure
# Set region to: ap-south-1

# Test access
$env:TEAM_NAME='trading-team'
python sample_trading-team.py
```

### 3. Basic Usage Example
```python
from examples.stock_client import StockDataClient

# Initialize client
client = StockDataClient('your-bucket-name')

# Get latest price
data = client.get_latest_price('RELIANCE')
print(f"RELIANCE: ₹{data['ohlcv']['close']}")

# Get historical data
from datetime import datetime, timedelta
historical = client.get_price_range(
    'RELIANCE', 
    datetime.now() - timedelta(days=7), 
    datetime.now()
)

# Convert to pandas DataFrame
df = client.to_dataframe(historical)
print(df.head())
```

## 📊 Available Data

### Symbols
- **Large Cap**: RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK
- **Consumer**: HINDUNILVR, ITC
- **Infrastructure**: LT
- **Telecom**: BHARTIARTL
- **Banking**: KOTAKBANK

### Data Format
```json
{
  "symbol": "RELIANCE",
  "timestamp": "2025-08-29T09:15:00Z",
  "ohlcv": {
    "open": 2450.50,
    "high": 2465.75,
    "low": 2448.20,
    "close": 2463.10,
    "volume": 1234567
  },
  "technical_indicators": {
    "sma_20": 2455.30,
    "rsi_14": 58.45
  }
}
```

### Update Frequency
- **Market Hours**: Every 15 minutes (9:15 AM - 3:30 PM IST)
- **Trading Days**: Monday to Friday (excluding holidays)
- **Data Latency**: < 2 minutes

## 🔧 Integration Patterns

### 1. Real-time Monitoring
```python
# Monitor price changes
def monitor_stock(symbol, threshold=2.0):
    client = StockDataClient(bucket_name)
    
    while True:
        data = client.get_latest_price(symbol)
        # Your logic here
        time.sleep(60)
```

### 2. Batch Analysis
```python
# Daily data analysis
def analyze_daily_data(symbols, date):
    client = StockDataClient(bucket_name)
    
    for symbol in symbols:
        data = client.get_historical_data(symbol, date)
        df = client.to_dataframe(data)
        # Your analysis here
```

### 3. Alert System
```python
# Price alert system
def setup_alerts():
    from examples.stock_client import RealTimeStockStream
    
    stream = RealTimeStockStream(sns_topic_arn)
    stream.subscribe_email('alerts@company.com')
```

## 📈 Use Cases by Team

### Trading Team
- Real-time price monitoring
- Technical indicator analysis
- Automated trading signals
- Portfolio performance tracking

### Analytics Team
- Historical trend analysis
- Market research
- Risk assessment
- Performance benchmarking

### Risk Management
- Position monitoring
- Volatility analysis
- Exposure calculation
- Compliance reporting

### Product Team
- Market data for apps
- Price display widgets
- Investment recommendations
- User portfolio tracking

## 🔐 Security & Permissions

### Required AWS Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": "arn:aws:s3:::stock-pipeline-dev-ohlcv-*"
        },
        {
            "Effect": "Allow", 
            "Action": ["sns:Subscribe"],
            "Resource": "arn:aws:sns:ap-south-1:*:stock-pipeline-alerts"
        }
    ]
}
```

### Best Practices
1. **Use IAM roles** instead of access keys when possible
2. **Implement caching** to reduce API calls
3. **Set up monitoring** for your data usage
4. **Handle errors gracefully** with retries
5. **Respect rate limits** to avoid throttling

## 💰 Cost Considerations

### S3 Costs
- GET Requests: $0.0004 per 1,000 requests
- Data Transfer: $0.09 per GB (if crossing regions)

### Typical Usage Costs
- **Light usage** (few requests/hour): $1-2/month
- **Moderate usage** (regular monitoring): $5-10/month  
- **Heavy usage** (real-time apps): $20-50/month

### Cost Optimization
- Cache frequently accessed data
- Use batch requests when possible
- Monitor usage with CloudWatch
- Set up billing alerts

## 🆘 Support & Troubleshooting

### Common Issues

**"NoSuchBucket" Error**
- Check bucket name in configuration
- Verify AWS region (should be ap-south-1)
- Confirm AWS credentials have S3 access

**"Access Denied" Error**
- Verify IAM permissions
- Check AWS credentials configuration
- Ensure correct bucket name

**"No Data Found" Error**
- Check if market is open
- Verify symbol name (use exact format)
- Check data availability for requested date

### Getting Help
- **Documentation**: `../API_INTEGRATION_GUIDE.md`
- **Issues**: Create GitHub issue with error details
- **Email**: data-platform-team@company.com
- **Slack**: #stock-data-api

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Your code here - will show detailed error messages
```

## 📚 Additional Resources

- **API Documentation**: `../API_INTEGRATION_GUIDE.md`
- **Configuration**: `../api_config.json`
- **Fyers API Docs**: https://fyers.in/api-documentation/
- **AWS S3 SDK**: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
- **Pandas Documentation**: https://pandas.pydata.org/docs/

---

*Need help? Contact the Data Platform Team at data-platform-team@company.com*
