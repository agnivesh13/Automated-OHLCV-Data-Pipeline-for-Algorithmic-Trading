-- Athena Table Definition for Lightweight ETL CSV Output
-- This table can query compressed CSV files directly

CREATE EXTERNAL TABLE IF NOT EXISTS ohlcv_csv (
  symbol string,
  symbol_clean string,
  timestamp_unix bigint,
  timestamp_iso timestamp,
  open double,
  high double,
  low double,
  close double,
  volume bigint,
  resolution string,
  fetch_timestamp string,
  hour int,
  processed_at timestamp
)
PARTITIONED BY (
  symbol string,
  year int,
  month int,
  day int
)
STORED AS TEXTFILE
LOCATION 's3://YOUR_BUCKET_NAME/analytics/csv/'
TBLPROPERTIES (
  'has_encrypted_data'='false',
  'skip.header.line.count'='1',
  'field.delim'=',',
  'compression.type'='gzip',
  'projection.enabled'='true',
  'projection.symbol.type'='enum',
  'projection.symbol.values'='RELIANCE,TCS,HDFCBANK,INFY,HINDUNILVR,ICICIBANK,KOTAKBANK,SBIN,BHARTIARTL,ITC,ASIANPAINT,LT,AXISBANK,MARUTI,SUNPHARMA,TITAN,ULTRACEMCO,NESTLEIND,WIPRO,MM',
  'projection.year.type'='integer',
  'projection.year.range'='2024,2030',
  'projection.month.type'='integer',
  'projection.month.range'='1,12',
  'projection.month.digits'='2',
  'projection.day.type'='integer',
  'projection.day.range'='1,31',
  'projection.day.digits'='2',
  'storage.location.template'='s3://YOUR_BUCKET_NAME/analytics/csv/symbol=${symbol}/year=${year}/month=${month}/day=${day}/'
);

-- Create a view for easier querying
CREATE OR REPLACE VIEW ohlcv_lightweight AS
SELECT 
  symbol_clean,
  timestamp_iso as timestamp,
  open,
  high,
  low,
  close,
  volume,
  resolution,
  year,
  month,
  day,
  hour,
  (close - open) as price_change,
  ((close - open) / open) * 100 as price_change_percent,
  (high - low) as daily_range,
  ((high - low) / open) * 100 as volatility_percent,
  processed_at
FROM ohlcv_csv
WHERE year >= 2025;

-- Example queries for CSV-based analytics

-- 1. Latest data for all symbols
SELECT symbol_clean, timestamp, close, volume
FROM ohlcv_lightweight
WHERE year = 2025 AND month = 10 AND day = 7
ORDER BY timestamp DESC
LIMIT 100;

-- 2. Daily summary by symbol
SELECT 
  symbol_clean,
  date(timestamp) as trade_date,
  MIN(low) as day_low,
  MAX(high) as day_high,
  first_value(open) OVER (
    PARTITION BY symbol_clean, date(timestamp) 
    ORDER BY timestamp ASC
  ) as day_open,
  last_value(close) OVER (
    PARTITION BY symbol_clean, date(timestamp) 
    ORDER BY timestamp ASC
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
  ) as day_close,
  SUM(volume) as total_volume,
  COUNT(*) as data_points
FROM ohlcv_lightweight
WHERE year = 2025 AND month = 10
GROUP BY symbol_clean, date(timestamp), open, close
ORDER BY trade_date DESC, total_volume DESC;

-- 3. Top performers by volume
SELECT 
  symbol_clean,
  SUM(volume) as total_volume,
  AVG(close) as avg_price,
  COUNT(*) as data_points,
  MAX(timestamp) as latest_time
FROM ohlcv_lightweight
WHERE year = 2025 AND month = 10
GROUP BY symbol_clean
ORDER BY total_volume DESC
LIMIT 10;

-- 4. Price movement analysis
SELECT 
  symbol_clean,
  AVG(price_change_percent) as avg_change_percent,
  STDDEV(price_change_percent) as volatility,
  MAX(price_change_percent) as max_gain,
  MIN(price_change_percent) as max_loss,
  COUNT(*) as total_intervals
FROM ohlcv_lightweight
WHERE year = 2025 AND month = 10
GROUP BY symbol_clean
ORDER BY volatility DESC;