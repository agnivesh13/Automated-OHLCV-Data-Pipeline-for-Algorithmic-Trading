"""Transformation helpers for the ETL job.

Functions are small and pure where possible to ease unit testing.
"""
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd


def normalize_record(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize a single raw record into the target schema.

    Expected to extract: symbol, timestamp, close, volume.
    Accepts a few common timestamp formats; returns None when required fields missing.
    """
    # Raw may have nested structures depending on ingestion source; be defensive
    symbol = raw.get("symbol") or raw.get("s") or raw.get("ticker")
    if not symbol:
        return None

    # timestamp: try numeric epoch (ms or s) or ISO strings
    ts = raw.get("timestamp") or raw.get("ts") or raw.get("time")
    if ts is None:
        return None

    # Normalize timestamp to pandas Timestamp
    try:
        if isinstance(ts, (int, float)):
            # heuristics: if large (>1e12) treat as ms
            if ts > 1e12:
                ts_val = pd.to_datetime(int(ts), unit="ms")
            elif ts > 1e9:
                ts_val = pd.to_datetime(int(ts), unit="s")
            else:
                ts_val = pd.to_datetime(int(ts), unit="s")
        else:
            ts_val = pd.to_datetime(str(ts))
    except Exception:
        return None

    # numeric fields
    close = raw.get("close") or raw.get("c") or raw.get("last")
    volume = raw.get("volume") or raw.get("v")

    try:
        close_val = float(close) if close is not None else None
    except Exception:
        close_val = None

    try:
        volume_val = int(volume) if volume is not None else None
    except Exception:
        volume_val = None

    if close_val is None:
        return None

    return {
        "symbol": symbol,
        "timestamp": ts_val.to_pydatetime(),
        "close": close_val,
        "volume": volume_val if volume_val is not None else 0,
        "ingested_at": datetime.utcnow(),
    }


def records_to_df(records):
    """Convert iterable of normalized records into a partitioned DataFrame (adds year/month/day columns).
    Returns pandas.DataFrame
    """
    df = pd.DataFrame(records)
    if df.empty:
        return df
    # Ensure timestamp is datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["ingested_at"] = pd.to_datetime(df["ingested_at"]) if "ingested_at" in df.columns else pd.Timestamp.utcnow()
    df["year"] = df["timestamp"].dt.year
    df["month"] = df["timestamp"].dt.month
    df["day"] = df["timestamp"].dt.day
    # Reorder columns to a predictable layout
    cols = ["symbol", "timestamp", "close", "volume", "ingested_at", "year", "month", "day"]
    return df[[c for c in cols if c in df.columns]]
