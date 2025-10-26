"""S3 helper utilities used by the ETL job.

Functions:
- list_objects_for_prefix(s3_client, bucket, prefix, date_prefix=None)
- download_json_obj(s3_client, bucket, key) -> dict
- write_parquet_dataframe(s3_client, df, bucket, key)

This module uses boto3 clients passed in (to ease testing/mocking).
"""
from io import BytesIO
import json
import logging
import boto3
import pandas as pd

logger = logging.getLogger(__name__)


def list_objects_for_prefix(s3_client, bucket: str, prefix: str, max_keys: int = 1000):
    """List object keys under a prefix. Returns list of keys.

    Note: simple paginator-aware implementation.
    """
    paginator = s3_client.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, PaginationConfig={"PageSize": 1000}):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
            if len(keys) >= max_keys:
                return keys
    return keys


def download_json_obj(s3_client, bucket: str, key: str):
    """Download object from S3 and parse JSON. Returns Python object (dict/list).

    Raises botocore exceptions on failures.
    """
    logger.debug("Downloading s3://%s/%s", bucket, key)
    resp = s3_client.get_object(Bucket=bucket, Key=key)
    body = resp["Body"].read()
    return json.loads(body)


def write_parquet_dataframe(s3_client, df: pd.DataFrame, bucket: str, key: str, engine: str = "pyarrow", compression: str = "snappy"):
    """Write pandas DataFrame to S3 as Parquet using a memory buffer.

    s3_client is expected to be boto3 client. The function writes bytes to S3 via put_object.
    """
    buffer = BytesIO()
    df.to_parquet(buffer, engine=engine, compression=compression, index=False)
    buffer.seek(0)
    logger.info("Uploading parquet to s3://%s/%s (%.2f KB)", bucket, key, len(buffer.getvalue()) / 1024.0)
    s3_client.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())
