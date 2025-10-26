-- Optimized Athena Table Definition for Parquet Files
-- Run this in Athena Console after data is processed

-- Create external table for OHLCV Parquet data
CREATE EXTERNAL TABLE IF NOT EXISTS ohlcv_data (
  symbol string,
  resolution string,
  timestamp_unix bigint,
  open double,
  high double,
  low double,
  close double,
  volume bigint,
  fetch_timestamp string,
  hour int,
  ingested_at timestamp
)
PARTITIONED BY (
  year int,
  month int,
  day int,
  symbol_clean string
)
STORED AS PARQUET
LOCATION 's3://YOUR_BUCKET_NAME/parquet/resolution=5/'
TBLPROPERTIES (
  'has_encrypted_data'='false',
  'projection.enabled'='true',
  'projection.year.type'='integer',
  'projection.year.range'='2024,2030',
  'projection.month.type'='integer',
  'projection.month.range'='1,12',
  'projection.month.digits'='2',
  'projection.day.type'='integer',
  'projection.day.range'='1,31',
  'projection.day.digits'='2',
  'projection.symbol_clean.type'='enum',
  'projection.symbol_clean.values'='RELIANCE,TCS,HDFCBANK,INFY,HINDUNILVR,ICICIBANK,KOTAKBANK,SBIN,BHARTIARTL,ITC,ASIANPAINT,LT,AXISBANK,MARUTI,SUNPHARMA,TITAN,ULTRACEMCO,NESTLEIND,WIPRO,MM',
  'storage.location.template'='s3://YOUR_BUCKET_NAME/parquet/resolution=5/year=${year}/month=${month}/day=${day}/symbol_clean=${symbol_clean}/'
);

-- Create a view for easy querying with computed timestamp
CREATE OR REPLACE VIEW ohlcv_view AS
SELECT 
  symbol,
  symbol_clean,
  resolution,
  from_unixtime(timestamp_unix) as timestamp,
  open,
  high,
  low,
  close,
  volume,
  fetch_timestamp,
  hour,
  ingested_at,
  year,
  month,
  day,
  -- Add computed columns for analysis
  (close - open) as price_change,
  ((close - open) / open) * 100 as price_change_percent,
  (high - low) as daily_range,
  ((high - low) / open) * 100 as volatility_percent
FROM ohlcv_data
WHERE year >= 2025;

-- Example queries for testing Parquet performance

-- 1. Latest data for all symbols
SELECT symbol_clean, timestamp, close, volume
FROM ohlcv_view
WHERE year = 2025 AND month = 8 AND day = 28
ORDER BY timestamp DESC
LIMIT 100;

-- 2. Top performers by volume
SELECT 
  symbol_clean,
  SUM(volume) as total_volume,
  AVG(close) as avg_price,
  COUNT(*) as data_points,
  MAX(timestamp) as latest_time
FROM ohlcv_view
WHERE year = 2025 AND month = 8
GROUP BY symbol_clean
ORDER BY total_volume DESC
LIMIT 10;

-- 3. Price movements analysis
SELECT 
  symbol_clean,
  date(timestamp) as trade_date,
  MIN(low) as day_low,
  MAX(high) as day_high,
  AVG(close) as avg_close,
  SUM(volume) as total_volume,
  COUNT(*) as intervals_count
FROM ohlcv_view
WHERE year = 2025 AND month = 8
GROUP BY symbol_clean, date(timestamp)
ORDER BY trade_date DESC, total_volume DESC;

-- 4. Volatility analysis
SELECT 
  symbol_clean,
  AVG(volatility_percent) as avg_volatility,
  STDDEV(price_change_percent) as price_volatility,
  MAX(price_change_percent) as max_gain,
  MIN(price_change_percent) as max_loss
FROM ohlcv_view
WHERE year = 2025 AND month = 8
GROUP BY symbol_clean
ORDER BY avg_volatility DESC;

-- 5. Performance comparison between symbols
WITH daily_summary AS (
  SELECT 
    symbol_clean,
    date(timestamp) as trade_date,
    first_value(open) OVER (
      PARTITION BY symbol_clean, date(timestamp) 
      ORDER BY timestamp ASC
    ) as day_open,
    last_value(close) OVER (
      PARTITION BY symbol_clean, date(timestamp) 
      ORDER BY timestamp ASC
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) as day_close,
    SUM(volume) OVER (
      PARTITION BY symbol_clean, date(timestamp)
    ) as day_volume
  FROM ohlcv_view
  WHERE year = 2025 AND month = 8
)
SELECT DISTINCT
  symbol_clean,
  trade_date,
  day_open,
  day_close,
  ((day_close - day_open) / day_open) * 100 as daily_return_percent,
  day_volume
FROM daily_summary
ORDER BY trade_date DESC, daily_return_percent DESC;
