#!/usr/bin/env python3
"""
Quick API Query Examples for CSV Data
Run specific queries against your S3 CSV partitions
"""

import boto3
import json
import gzip
import io
import csv
from datetime import datetime, timedelta

# Configuration
S3_BUCKET = "stock-pipeline-mvp-dev-ohlcv-5e23bf76"
CSV_PREFIX = "analytics/csv/"


def query_single_symbol_date_range(symbol, from_date, to_date):
    """
    Query OHLCV data for a single symbol within date range
    
    Example:
        query_single_symbol_date_range('RELIANCE', '2025-10-08', '2025-10-10')
    """
    print(f"\n{'='*60}")
    print(f"Querying {symbol} from {from_date} to {to_date}")
    print(f"{'='*60}")
    
    s3 = boto3.client('s3')
    
    # Parse dates
    from_dt = datetime.strptime(from_date, '%Y-%m-%d')
    to_dt = datetime.strptime(to_date, '%Y-%m-%d')
    
    all_candles = []
    current_dt = from_dt
    
    while current_dt <= to_dt:
        prefix = f"{CSV_PREFIX}symbol={symbol}/year={current_dt.year}/month={current_dt.month:02d}/day={current_dt.day:02d}/"
        
        try:
            response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.endswith('.csv') or key.endswith('.csv.gz'):
                        # Read CSV file
                        file_response = s3.get_object(Bucket=S3_BUCKET, Key=key)
                        content = file_response['Body'].read()
                        
                        if key.endswith('.gz'):
                            content = gzip.decompress(content)
                        
                        csv_text = content.decode('utf-8')
                        reader = csv.DictReader(io.StringIO(csv_text))
                        
                        for row in reader:
                            all_candles.append({
                                'timestamp': int(row['timestamp_unix']),
                                'datetime': row['timestamp_iso'],
                                'open': float(row['open']),
                                'high': float(row['high']),
                                'low': float(row['low']),
                                'close': float(row['close']),
                                'volume': int(float(row['volume']))
                            })
        except Exception as e:
            print(f"  Warning: {current_dt.strftime('%Y-%m-%d')}: {e}")
        
        current_dt += timedelta(days=1)
    
    # Deduplicate and sort
    unique_candles = {c['timestamp']: c for c in all_candles}
    sorted_candles = sorted(unique_candles.values(), key=lambda x: x['timestamp'])
    
    print(f"\n✅ Retrieved {len(sorted_candles)} candles")
    
    if sorted_candles:
        print(f"\nFirst 5 candles:")
        for candle in sorted_candles[:5]:
            print(f"  {candle['datetime']}: O={candle['open']:.2f} H={candle['high']:.2f} L={candle['low']:.2f} C={candle['close']:.2f} V={candle['volume']}")
        
        if len(sorted_candles) > 5:
            print(f"\nLast 5 candles:")
            for candle in sorted_candles[-5:]:
                print(f"  {candle['datetime']}: O={candle['open']:.2f} H={candle['high']:.2f} L={candle['low']:.2f} C={candle['close']:.2f} V={candle['volume']}")
    
    return sorted_candles


def query_multiple_symbols(symbols, date):
    """
    Query latest prices for multiple symbols on a specific date
    
    Example:
        query_multiple_symbols(['RELIANCE', 'TCS', 'INFY'], '2025-10-08')
    """
    print(f"\n{'='*60}")
    print(f"Querying {len(symbols)} symbols for {date}")
    print(f"{'='*60}")
    
    results = {}
    
    for symbol in symbols:
        candles = query_single_symbol_date_range(symbol, date, date)
        if candles:
            results[symbol] = {
                'latest_price': candles[-1]['close'],
                'high': max(c['high'] for c in candles),
                'low': min(c['low'] for c in candles),
                'volume': sum(c['volume'] for c in candles),
                'candles_count': len(candles)
            }
    
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    
    for symbol, data in results.items():
        print(f"\n{symbol}:")
        print(f"  Latest Price: ${data['latest_price']:.2f}")
        print(f"  Day High: ${data['high']:.2f}")
        print(f"  Day Low: ${data['low']:.2f}")
        print(f"  Total Volume: {data['volume']:,}")
        print(f"  Candles: {data['candles_count']}")
    
    return results


def get_available_symbols():
    """Get list of all available symbols from S3"""
    print(f"\nFetching available symbols...")
    
    s3 = boto3.client('s3')
    response = s3.list_objects_v2(
        Bucket=S3_BUCKET,
        Prefix=CSV_PREFIX,
        Delimiter='/'
    )
    
    symbols = []
    if 'CommonPrefixes' in response:
        for prefix in response['CommonPrefixes']:
            symbol_prefix = prefix['Prefix']
            if 'symbol=' in symbol_prefix:
                symbol = symbol_prefix.split('symbol=')[1].strip('/')
                symbols.append(symbol)
    
    print(f"✅ Found {len(symbols)} symbols: {', '.join(sorted(symbols))}")
    return sorted(symbols)


def get_available_dates_for_symbol(symbol, limit=10):
    """Get available dates for a symbol"""
    print(f"\nFetching available dates for {symbol}...")
    
    s3 = boto3.client('s3')
    prefix = f"{CSV_PREFIX}symbol={symbol}/"
    
    dates = set()
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    # Extract date from path: symbol=X/year=Y/month=M/day=D/
                    parts = key.split('/')
                    for i, part in enumerate(parts):
                        if part.startswith('year=') and i+2 < len(parts):
                            year = parts[i].split('=')[1]
                            month = parts[i+1].split('=')[1]
                            day = parts[i+2].split('=')[1]
                            dates.add(f"{year}-{month}-{day}")
    except Exception as e:
        print(f"  Error: {e}")
    
    sorted_dates = sorted(dates, reverse=True)[:limit]
    
    print(f"✅ Found {len(dates)} total dates")
    print(f"Latest {limit} dates:")
    for date in sorted_dates:
        print(f"  - {date}")
    
    return sorted_dates


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║  Quick API Query Examples                             ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    # Example 1: Get available symbols
    print("\n1️⃣ Example 1: List all available symbols")
    symbols = get_available_symbols()
    
    # Example 2: Get available dates for a symbol
    print("\n2️⃣ Example 2: Check available dates for RELIANCE")
    dates = get_available_dates_for_symbol('RELIANCE', limit=5)
    
    # Example 3: Query single symbol for date range
    print("\n3️⃣ Example 3: Query RELIANCE for October 8, 2025")
    candles = query_single_symbol_date_range('RELIANCE', '2025-10-08', '2025-10-08')
    
    # Example 4: Query multiple symbols
    print("\n4️⃣ Example 4: Query multiple symbols for October 8, 2025")
    results = query_multiple_symbols(['RELIANCE', 'TCS', 'INFY'], '2025-10-08')
    
    print(f"\n{'='*60}")
    print("✅ All examples completed!")
    print(f"{'='*60}")
    
    print("""
    
    To run specific queries, import this file and call:
    
    1. get_available_symbols()
       - Returns list of all symbols
    
    2. get_available_dates_for_symbol('RELIANCE', limit=10)
       - Returns available dates for a symbol
    
    3. query_single_symbol_date_range('RELIANCE', '2025-10-08', '2025-10-10')
       - Returns OHLCV candles for date range
    
    4. query_multiple_symbols(['RELIANCE', 'TCS'], '2025-10-08')
       - Returns latest prices and stats for multiple symbols
    """)
