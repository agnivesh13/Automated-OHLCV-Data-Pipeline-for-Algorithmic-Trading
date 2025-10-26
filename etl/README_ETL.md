# Python ETL -> Parquet (analytics)

This directory contains a production-ready Python ETL that reads raw JSON from S3 under `/Raw data/Prices/{date}/`, extracts a reduced OHLCV schema (close-only), and writes partitioned Parquet files under `/Company Data/{Security_ID}/Prices/`.

## Files
- `python_etl/` - package with `s3_helpers.py` and `transforms.py`.
- `python_etl_job.py` - CLI and `lambda_handler` entrypoint for scheduling/manual runs.
- `requirements.txt` - Python packages required (for local testing or Lambda packaging).

## Athena table (example)

CREATE EXTERNAL TABLE ohlcv_close_only (
  symbol string,
  timestamp timestamp,
  close double,
  volume bigint,
  ingested_at timestamp
)
PARTITIONED BY (year int, month int, day int)
STORED AS PARQUET
LOCATION 's3://<bucket>/Company Data/<Security_ID>/Prices/'

-- After creating the table, run MSCK REPAIR TABLE ohlcv_close_only; or use ALTER TABLE ADD PARTITION for partitions.

## Sample queries


-- Latest close for a symbol
SELECT symbol, close, timestamp
FROM ohlcv_close_only
WHERE symbol = 'RELIANCE' AND year=2025 AND month=1 AND day=10
ORDER BY timestamp DESC
LIMIT 1;

-- Daily aggregation
SELECT symbol, year, month, day, avg(close) as avg_close, sum(volume) as total_volume
FROM ohlcv_close_only
GROUP BY symbol, year, month, day
ORDER BY year, month, day DESC
LIMIT 100;

## How to run


Local/CLI (with AWS credentials configured):

```powershell
python .\etl\python_etl_job.py --date 2025-01-10 --bucket your-bucket-name
```

Lambda packaging notes:
- Install dependencies and package the `etl/` directory and dependencies into a deployment zip, or use a Lambda Layer for pandas/pyarrow due to size.
- Ensure environment variable: `ETL_S3_BUCKET` (required).

Raw data must be under `/Raw data/Prices/{date}/` and Parquet will be written to `/Company Data/{Security_ID}/Prices/`.
