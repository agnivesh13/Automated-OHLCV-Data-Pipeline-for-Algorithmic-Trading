"""Python ETL package for Price Feed Parser

This package contains small, testable helpers to read raw JSON from S3,
transform into a reduced OHLCV (close-only) schema and write Parquet files
back to S3 under the `analytics/` prefix.

Keep functions small and side-effect free where possible to ease unit testing.
"""

__all__ = [
    "s3_helpers",
    "transforms",
]
