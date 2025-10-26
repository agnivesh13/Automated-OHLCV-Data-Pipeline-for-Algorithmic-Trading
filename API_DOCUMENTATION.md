# Stock Data API Documentation - LIVE & WORKING! 🚀

## ⚡ **API Status: DEPLOYED & OPERATIONAL**

Your REST API is **live and fully functional**! Other teams can start querying stock data immediately.

**Base URL:**
```
https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev
```

**Lambda Function:** `stock-pipeline-mvp-api-handler`  
**Data Source:** S3 Raw JSON files (`Raw data/Prices/`)  
**Cost:** **$0.00/month** (100% FREE TIER)  
**Update Frequency:** Every 5 minutes during trading hours

---

## 📋 Quick Start

```bash
# Test the API now!
curl "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/symbols"
```

---

## Overview
The Stock Data API provides REST endpoints for accessing real-time and historical OHLCV (Open, High, Low, Close, Volume) data for Indian stock market symbols.

## Base URL
```
https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev
```

## 📊 **Data Source & Architecture**

### Where API Gets Data From
- **Source:** S3 bucket `Raw data/Prices/` folder
- **Format:** Raw JSON files created by ingestion Lambda
- **Update:** Every 5 minutes during market hours (9:15 AM - 3:30 PM IST)
- **NOT USING:** Analytics CSV files (those are for Athena/analytics only)

### Why Raw JSON (Not CSV)?
✅ **Real-time:** Updated every 5 minutes (vs CSV once daily)  
✅ **Faster:** Single file contains all symbols  
✅ **Simpler:** Direct JSON parsing, less code  
✅ **Better for APIs:** Designed for quick queries

### Data Flow
```
Fyers API → Ingestion Lambda (every 5 min) → Raw JSON (S3) → API Handler → REST API Response
```

---

## Authentication
Currently, no authentication is required. The API uses CORS headers to allow cross-origin requests.

## Endpoints

### 1. List Available Symbols
**GET** `/symbols`

Returns a list of all available stock symbols in the system.

**Query Parameters:**
- `limit` (optional): Maximum number of symbols to return

**Example Request:**
```bash
curl "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/symbols"
curl "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/symbols?limit=5"
```

**Example Response:**
```json
{
  "symbols": [
    "NSE:BHARTIARTL-EQ",
    "NSE:HDFCBANK-EQ",
    "NSE:HINDUNILVR-EQ",
    "NSE:ICICIBANK-EQ",
    "NSE:INFY-EQ",
    "NSE:ITC-EQ",
    "NSE:KOTAKBANK-EQ",
    "NSE:RELIANCE-EQ",
    "NSE:SBIN-EQ",
    "NSE:TCS-EQ"
  ],
  "count": 10,
  "timestamp": "2025-09-03T15:20:00Z"
}
```

### 2. Get OHLCV Data for Specific Symbol
**GET** `/ohlcv/{symbol}`

Returns OHLCV candlestick data for a specific symbol.

**Path Parameters:**
- `symbol` (required): Stock symbol (e.g., NSE:RELIANCE-EQ)

**Query Parameters:**
- `from` (optional): Start date in YYYY-MM-DD format
- `to` (optional): End date in YYYY-MM-DD format
- `interval` (optional): Time interval in minutes (default: 5)
- `limit` (optional): Maximum number of candles to return

**Example Request:**
```bash
curl "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/ohlcv/NSE:RELIANCE-EQ"
curl "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/ohlcv/NSE:RELIANCE-EQ?limit=10"
```

**Example Response:**
```json
{
  "symbol": "NSE:RELIANCE-EQ",
  "interval": "5",
  "data": [
    {
      "timestamp": 1725364800,
      "datetime": "2025-09-03T09:20:00Z",
      "open": 2850.50,
      "high": 2855.75,
      "low": 2848.25,
      "close": 2853.00,
      "volume": 125000
    }
  ],
  "count": 1,
  "timestamp": "2025-09-03T15:20:00Z"
}
```

### 3. Get Latest Data for Multiple Symbols
**GET** `/latest`

Returns the most recent data for specified symbols.

**Query Parameters:**
- `symbols` (optional): Comma-separated list of symbols (if not provided, returns data for top 10 symbols)

**Example Request:**
```bash
curl "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/latest"
curl "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/latest?symbols=NSE:RELIANCE-EQ,NSE:TCS-EQ"
```

**Example Response:**
```json
{
  "symbols": ["NSE:RELIANCE-EQ", "NSE:TCS-EQ"],
  "data": {
    "NSE:RELIANCE-EQ": {
      "symbol": "NSE:RELIANCE-EQ",
      "latest_price": 2853.00,
      "total_candles": 75,
      "resolution": "5",
      "timestamp": 1725364800,
      "last_candle": [1725364800, 2850.50, 2855.75, 2848.25, 2853.00, 125000]
    }
  },
  "count": 2,
  "timestamp": "2025-09-03T15:20:00Z"
}
```

### 4. Get Historical Data (Bulk Export)
**GET** `/historical`

Returns bulk historical data for analysis and batch processing.

**Query Parameters:**
- `symbol` (optional): Single symbol to fetch
- `symbols` (optional): Comma-separated list of symbols
- `from` (optional): Start date in YYYY-MM-DD format
- `to` (optional): End date in YYYY-MM-DD format
- `format` (optional): Response format ('json' or 'csv', default: 'json')

**Example Request:**
```bash
curl "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/historical?symbol=NSE:RELIANCE-EQ"
curl "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/historical?symbols=NSE:RELIANCE-EQ,NSE:TCS-EQ&format=csv"
```

**Example Response (JSON):**
```json
{
  "symbols": ["NSE:RELIANCE-EQ"],
  "from_date": null,
  "to_date": null,
  "data": {
    "NSE:RELIANCE-EQ": {
      "symbol": "NSE:RELIANCE-EQ",
      "candles": [
        {
          "timestamp": 1725364800,
          "datetime": "2025-09-03T09:20:00Z",
          "open": 2850.50,
          "high": 2855.75,
          "low": 2848.25,
          "close": 2853.00,
          "volume": 125000
        }
      ],
      "count": 1
    }
  },
  "total_records": 1,
  "timestamp": "2025-09-03T15:20:00Z"
}
```

**Example Response (CSV):**
```csv
symbol,timestamp,datetime,open,high,low,close,volume
NSE:RELIANCE-EQ,1725364800,2025-09-03T09:20:00Z,2850.50,2855.75,2848.25,2853.00,125000
```

## Error Responses

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (symbol not found)
- `500`: Internal Server Error

**Error Response Format:**
```json
{
  "error": "Error type",
  "message": "Detailed error message",
  "symbol": "NSE:RELIANCE-EQ" // if applicable
}
```

## Rate Limits

- **Current**: No rate limits enforced
- **Future**: May implement rate limiting for fair usage

## Data Format

### Symbol Format
All symbols follow the format: `NSE:{SYMBOL_NAME}-EQ`

Examples:
- `NSE:RELIANCE-EQ` (Reliance Industries)
- `NSE:TCS-EQ` (Tata Consultancy Services)
- `NSE:HDFCBANK-EQ` (HDFC Bank)

### Timestamp Format
- **Unix Timestamp**: Number of seconds since January 1, 1970 UTC
- **ISO 8601**: YYYY-MM-DDTHH:mm:ssZ format for human-readable dates

### OHLCV Candle Format
Each candle contains:
- `timestamp`: Unix timestamp
- `datetime`: ISO 8601 formatted date/time
- `open`: Opening price
- `high`: Highest price
- `low`: Lowest price
- `close`: Closing price
- `volume`: Trading volume

## Integration Examples

### JavaScript/Node.js
```javascript
const axios = require('axios');

const API_BASE = 'https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev';

async function getSymbols() {
  const response = await axios.get(`${API_BASE}/symbols`);
  return response.data.symbols;
}

async function getOHLCV(symbol, limit = 100) {
  const response = await axios.get(`${API_BASE}/ohlcv/${symbol}?limit=${limit}`);
  return response.data.data;
}

async function getLatestData(symbols) {
  const symbolsParam = symbols.join(',');
  const response = await axios.get(`${API_BASE}/latest?symbols=${symbolsParam}`);
  return response.data.data;
}
```

### Python
```python
import requests
import pandas as pd

API_BASE = 'https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev'

def get_symbols():
    response = requests.get(f'{API_BASE}/symbols')
    return response.json()['symbols']

def get_ohlcv(symbol, limit=100):
    response = requests.get(f'{API_BASE}/ohlcv/{symbol}?limit={limit}')
    return response.json()['data']

def get_historical_csv(symbols):
    symbols_param = ','.join(symbols)
    response = requests.get(f'{API_BASE}/historical?symbols={symbols_param}&format=csv')
    # Convert to pandas DataFrame
    from io import StringIO
    return pd.read_csv(StringIO(response.text))
```

### cURL Examples
```bash
# Get all symbols
curl -X GET "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/symbols"

# Get OHLCV data for Reliance
curl -X GET "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/ohlcv/NSE:RELIANCE-EQ?limit=50"

# Get latest data for multiple symbols
curl -X GET "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/latest?symbols=NSE:RELIANCE-EQ,NSE:TCS-EQ,NSE:HDFCBANK-EQ"

# Export historical data as CSV
curl -X GET "https://jbw2maikhd.execute-api.ap-south-1.amazonaws.com/dev/historical?symbols=NSE:RELIANCE-EQ&format=csv" -o reliance_data.csv
```

### 5. AlfaQuantz Price Endpoint (path & query style)

This endpoint provides a compact way to request aggregated OHLCV candles for a symbol over a period. It supports both a path-style and query-style interface and can aggregate raw 5-minute candles into larger intervals (for example 10m, 1h, 1d).

Path-style:
```
/alfaquantz/price/get/{symbol},{interval},{period}
```

Query-style:
```
/alfaquantz/price/get?symbol={symbol}&interval={interval}&period={period}
```

Where:
- `symbol`: symbol name (e.g., `infy` or `NSE:INFY-EQ`) — symbol is normalized to `NSE:SYMBOL-EQ`.
- `interval`: aggregation interval (e.g., `10m`, `5m`, `1h`, `1d`). Use `10m` for ten-minute aggregation.
- `period`: lookback period (e.g., `3m` = 3 months, `30d` = 30 days, `2y` = 2 years). Months are approximated as 30 days and years as 365 days for the MVP.

Example requests:
```bash
# Path-style (3 month history aggregated to 10-minute candles)
curl "https://<api_base>/alfaquantz/price/get/infy,10m,3m"

# Query-style (same)
curl "https://<api_base>/alfaquantz/price/get?symbol=infy&interval=10m&period=3m"
```

Response shape:
- JSON object with keys: `symbol_requested`, `symbol_normalized`, `interval`, `period`, `from_date`, `to_date`, `count`, `candles`, `timestamp`.
- `candles` is an array of list-style candles: `[bucket_start_unix_ts, open, high, low, close, volume]`.

Example response (truncated):
```json
{
  "symbol_requested": "infy",
  "symbol_normalized": "NSE:INFY-EQ",
  "interval": "10m",
  "period": "3m",
  "from_date": "2025-07-30",
  "to_date": "2025-10-30",
  "count": 900,
  "candles": [
    [1698660000, 1500.5, 1504.0, 1498.5, 1502.0, 12345],
    [1698660600, 1502.0, 1503.5, 1500.0, 1501.0, 9876]
  ],
  "timestamp": "2025-10-30T12:00:00Z"
}
```

Aggregation details & caveats:
- Aggregation buckets are epoch-aligned (e.g., 10-minute buckets start at Unix timestamps that are multiples of 600). If you need market-session alignment (Asia/Kolkata trading day), request that specifically and we can change alignment.
- Aggregation expects raw data at equal-to-or-finer granularity (the ingestion pipeline collects 5-minute candles). Aggregating from 5m -> 10m is supported. Aggregating to intervals smaller than raw granularity (e.g., requesting 1m when only 5m data exists) will not produce correct results.
- Period parsing uses simple approximations: `m = 30 days`, `y = 365 days` for the MVP. For precise calendar-month ranges we can implement month-aware arithmetic.
- Data availability is limited by the MVP storage (recent JSON files in S3). Long-range requests (years) may return incomplete results. For reliable long-range querying we recommend partitioned Parquet + Athena.

Performance & usage:
- The endpoint reads recent S3 JSON files and performs aggregation on the Lambda at request time. For heavy usage or large lookbacks, consider pre-aggregating data or querying Parquet/columnar stores.

Security:
- This endpoint currently has no authentication. Consider adding API keys, Cognito, or IP allowlisting for production use.

## Data Availability

- **Market Hours**: Data is collected during Indian market hours (9:15 AM - 3:30 PM IST)
- **Update Frequency**: Every 5 minutes during market hours
- **Historical Data**: Available for the last 30 days
- **Symbols Covered**: Top 10 Indian equity stocks (Nifty 50 companies)

## Support and Issues

For API issues or feature requests, contact the data platform team:
- **Team**: Stock Data Platform
- **Environment**: Development/MVP
- **Infrastructure**: AWS API Gateway + Lambda
- **Data Source**: Fyers API (5-minute OHLCV data)

## Data Disclaimer

This API provides market data for development and testing purposes. For production trading or financial decisions, please use certified market data providers and ensure compliance with regulatory requirements.
