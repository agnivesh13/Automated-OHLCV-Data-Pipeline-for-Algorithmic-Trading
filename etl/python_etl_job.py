"""ETL job entrypoint for converting raw JSON in S3 to Parquet analytics.

Provides:
- lambda_handler(event, context): single-day run driven by ENV vars
- main() CLI for local/backfill runs
"""
import os
import argparse
import logging
import boto3
from datetime import datetime, timedelta
from typing import List

from etl.python_etl import s3_helpers, transforms

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


DEFAULT_BUCKET = os.environ.get("ETL_S3_BUCKET") or os.environ.get("S3_BUCKET")



def process_keys(s3_client, bucket: str, keys: List[str], out_prefix: str, batch_size: int = 100):
    """Process a list of S3 keys: download, transform, and write parquet batches.
    Returns number of records processed.
    """
    processed = 0
    normalized = []
    for key in keys:
        raw = s3_helpers.download_json_obj(s3_client, bucket, key)
        # raw might be a list or single dict
        if isinstance(raw, list):
            items = raw
        else:
            items = [raw]

        for it in items:
            nr = transforms.normalize_record(it)
            if nr:
                normalized.append(nr)
        # flush batch
        if len(normalized) >= batch_size:
            df = transforms.records_to_df(normalized)
            if not df.empty:
                ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                out_key = f"{out_prefix}part-{ts}-{processed}.parquet"
                s3_helpers.write_parquet_dataframe(s3_client, df, bucket, out_key)
                processed += len(df)
            normalized = []

    # final flush
    if normalized:
        df = transforms.records_to_df(normalized)
        if not df.empty:
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            out_key = f"{out_prefix}part-{ts}-{processed}.parquet"
            s3_helpers.write_parquet_dataframe(s3_client, df, bucket, out_key)
            processed += len(df)

    return processed


def run_for_date(run_date: datetime, bucket: str, raw_prefix: str, analytics_prefix: str):
    s3_client = boto3.client("s3")
    # Production raw data path: /Raw data/Prices/{date}/
    date_str = f"{run_date.year}-{run_date.month:02d}-{run_date.day:02d}"
    date_prefix = f"Raw data/Prices/{date_str}/"
    keys = s3_helpers.list_objects_for_prefix(s3_client, bucket, date_prefix)
    if not keys:
        logger.info("No keys found for date %s (prefix=%s)", run_date.date(), date_prefix)
        return 0
    processed = 0
    # For each key, process and write to /Company Data/{Security_ID}/Prices/
    for key in keys:
        raw = s3_helpers.download_json_obj(s3_client, bucket, key)
        if isinstance(raw, list):
            items = raw
        else:
            items = [raw]
        # Group by security_id
        by_sec = {}
        for it in items:
            nr = transforms.normalize_record(it)
            if nr:
                sec_id = nr["symbol"]
                by_sec.setdefault(sec_id, []).append(nr)
        for sec_id, records in by_sec.items():
            df = transforms.records_to_df(records)
            if not df.empty:
                ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                out_prefix = f"Company Data/{sec_id}/Prices/"
                out_key = f"{out_prefix}part-{ts}.parquet"
                s3_helpers.write_parquet_dataframe(s3_client, df, bucket, out_key)
                processed += len(df)
    logger.info("Processed %d records for date %s", processed, run_date.date())
    return processed


def lambda_handler(event, context):
    # Expect environment variables: ETL_S3_BUCKET and optionally a 'date' in event (YYYY-MM-DD)
    bucket = os.environ.get("ETL_S3_BUCKET") or DEFAULT_BUCKET
    if bucket is None:
        raise ValueError("ETL_S3_BUCKET must be set in environment")

    date_str = None
    if isinstance(event, dict):
        date_str = event.get("date") or event.get("run_date")

    if date_str:
        run_date = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        run_date = datetime.utcnow() - timedelta(days=1)

    # Only production paths used
    return {"processed": run_for_date(run_date, bucket, None, None)}


def main():
    parser = argparse.ArgumentParser(description="Run ETL to convert raw JSON to Parquet in S3")
    parser.add_argument("--date", help="Date to process in YYYY-MM-DD (defaults to yesterday)")
    parser.add_argument("--bucket", help="S3 bucket override")
    # No prefix overrides; production paths only
    args = parser.parse_args()

    bucket = args.bucket or DEFAULT_BUCKET
    if bucket is None:
        parser.error("S3 bucket must be provided via --bucket or ETL_S3_BUCKET env var")

    if args.date:
        run_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        run_date = datetime.utcnow() - timedelta(days=1)

    processed = run_for_date(run_date, bucket, None, None)
    print(f"Processed {processed} records for date {run_date.date()}")


if __name__ == "__main__":
    main()
