"""
AWS Lambda Analytics Function for Stock OHLCV Data
NO PANDAS - Uses native Python + CSV module + boto3
100% FREE TIER - Works in Mumbai (ap-south-1) region

Query Types:
1. symbol_stats - Get statistics for a single symbol on a date
2. daily_summary - Get summary for all symbols on a date
3. date_range - Get data for a symbol over date range
4. top_movers - Get top gainers/losers for a date
"""

import json
import boto3
import csv
import gzip
from io import StringIO, BytesIO
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os

# Initialize S3 client
s3_client = boto3.client('s3')

# Get bucket from environment
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'stock-pipeline-mvp')
CSV_PREFIX = os.environ.get('CSV_PREFIX', 'analytics/csv')


def lambda_handler(event, context):
    """
    Main Lambda handler - routes to query functions
    
    Event format:
    {
        "query_type": "symbol_stats|daily_summary|date_range|top_movers",
        "symbol": "RELIANCE",
        "date": "2025-10-07",
        "start_date": "2025-10-01",
        "end_date": "2025-10-07",
        "limit": 10
    }
    """
    try:
        query_type = event.get('query_type', 'symbol_stats')
        
        # Route to appropriate query function
        if query_type == 'symbol_stats':
            return symbol_stats(event)
        elif query_type == 'daily_summary':
            return daily_summary(event)
        elif query_type == 'date_range':
            return date_range_query(event)
        elif query_type == 'top_movers':
            return top_movers(event)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown query_type: {query_type}'})
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def read_csv_from_s3(symbol: str, year: int, month: int, day: int) -> Optional[List[Dict[str, Any]]]:
    """
    Read CSV file from S3 for a specific symbol and date
    Returns list of dictionaries (one per row)
    
    Returns None if file doesn't exist
    """
    try:
        # Construct S3 key with partitioning
        key = f'{CSV_PREFIX}/symbol={symbol}/year={year}/month={month:02d}/day={day:02d}/data.csv.gz'
        
        print(f"Reading s3://{BUCKET_NAME}/{key}")
        
        # Get object from S3
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        
        # Decompress gzip content
        compressed_data = response['Body'].read()
        decompressed_data = gzip.decompress(compressed_data).decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.DictReader(StringIO(decompressed_data))
        records = list(csv_reader)
        
        # Convert numeric fields
        for record in records:
            record['open'] = float(record['open'])
            record['high'] = float(record['high'])
            record['low'] = float(record['low'])
            record['close'] = float(record['close'])
            record['volume'] = int(record['volume'])
            record['timestamp_unix'] = int(record['timestamp_unix'])
        
        return records
    
    except s3_client.exceptions.NoSuchKey:
        print(f"File not found: s3://{BUCKET_NAME}/{key}")
        return None
    except Exception as e:
        print(f"Error reading CSV: {str(e)}")
        raise


def calculate_stats(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate statistics from a list of OHLCV records
    Native Python implementation (no Pandas)
    """
    if not records:
        return {}
    
    first_open = records[0]['open']
    last_close = records[-1]['close']
    
    # Calculate max high and min low
    high_values = [r['high'] for r in records]
    low_values = [r['low'] for r in records]
    close_values = [r['close'] for r in records]
    volume_values = [r['volume'] for r in records]
    
    max_high = max(high_values)
    min_low = min(low_values)
    total_volume = sum(volume_values)
    avg_close = sum(close_values) / len(close_values)
    
    price_change = last_close - first_open
    price_change_pct = (price_change / first_open) * 100 if first_open != 0 else 0
    
    return {
        'open': first_open,
        'close': last_close,
        'high': max_high,
        'low': min_low,
        'volume': total_volume,
        'avg_price': avg_close,
        'price_change': price_change,
        'price_change_pct': price_change_pct,
        'num_records': len(records)
    }


def symbol_stats(event: Dict) -> Dict:
    """
    Get statistics for a single symbol on a specific date
    
    Input:
        {
            "symbol": "RELIANCE",
            "date": "2025-10-07"
        }
    
    Output:
        {
            "symbol": "RELIANCE",
            "date": "2025-10-07",
            "stats": {
                "open": 2500.0,
                "close": 2520.5,
                "high": 2535.75,
                "low": 2495.0,
                "volume": 15000000,
                "price_change": 20.5,
                "price_change_pct": 0.82,
                "num_records": 96
            }
        }
    """
    symbol = event.get('symbol')
    date_str = event.get('date')
    
    if not symbol or not date_str:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing symbol or date'})
        }
    
    # Parse date
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    
    # Read CSV
    records = read_csv_from_s3(symbol, dt.year, dt.month, dt.day)
    
    if not records:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': f'No data found for {symbol} on {date_str}'})
        }
    
    # Calculate statistics
    stats = calculate_stats(records)
    
    result = {
        'symbol': symbol,
        'date': date_str,
        'stats': stats
    }
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }


def list_symbols_for_date(year: int, month: int, day: int) -> List[str]:
    """
    List all symbols that have data for a specific date
    """
    try:
        # List all symbol partitions
        prefix = f'{CSV_PREFIX}/symbol='
        
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=prefix,
            Delimiter='/'
        )
        
        if 'CommonPrefixes' not in response:
            return []
        
        symbols = []
        for obj in response['CommonPrefixes']:
            # Extract symbol from prefix (e.g., 'analytics/csv/symbol=RELIANCE/' -> 'RELIANCE')
            symbol = obj['Prefix'].split('symbol=')[1].rstrip('/')
            
            # Check if this symbol has data for the specific date
            date_key = f'{CSV_PREFIX}/symbol={symbol}/year={year}/month={month:02d}/day={day:02d}/'
            
            try:
                date_response = s3_client.list_objects_v2(
                    Bucket=BUCKET_NAME,
                    Prefix=date_key,
                    MaxKeys=1
                )
                
                if 'Contents' in date_response and len(date_response['Contents']) > 0:
                    symbols.append(symbol)
            except:
                continue
        
        return symbols
    
    except Exception as e:
        print(f"Error listing symbols: {str(e)}")
        return []


def daily_summary(event: Dict) -> Dict:
    """
    Get summary statistics for ALL symbols on a specific date
    
    Input:
        {
            "date": "2025-10-07"
        }
    
    Output:
        {
            "date": "2025-10-07",
            "summary": [
                {
                    "symbol": "RELIANCE",
                    "open": 2500.0,
                    "close": 2520.5,
                    "price_change_pct": 0.82,
                    "volume": 15000000
                },
                ...
            ],
            "total_symbols": 30
        }
    """
    date_str = event.get('date')
    
    if not date_str:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing date'})
        }
    
    # Parse date
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    
    # List all symbols for this date
    symbols = list_symbols_for_date(dt.year, dt.month, dt.day)
    
    if not symbols:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': f'No data found for {date_str}'})
        }
    
    # Get stats for each symbol
    summary = []
    for symbol in symbols:
        records = read_csv_from_s3(symbol, dt.year, dt.month, dt.day)
        
        if records:
            stats = calculate_stats(records)
            
            summary.append({
                'symbol': symbol,
                'open': stats['open'],
                'close': stats['close'],
                'high': stats['high'],
                'low': stats['low'],
                'volume': stats['volume'],
                'price_change_pct': stats['price_change_pct']
            })
    
    # Sort by price change percentage (descending)
    summary.sort(key=lambda x: x['price_change_pct'], reverse=True)
    
    result = {
        'date': date_str,
        'summary': summary,
        'total_symbols': len(summary)
    }
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }


def date_range_query(event: Dict) -> Dict:
    """
    Get data for a symbol over a date range
    
    Input:
        {
            "symbol": "RELIANCE",
            "start_date": "2025-10-01",
            "end_date": "2025-10-07"
        }
    
    Output:
        {
            "symbol": "RELIANCE",
            "start_date": "2025-10-01",
            "end_date": "2025-10-07",
            "data": [
                {
                    "date": "2025-10-01",
                    "open": 2480.0,
                    "close": 2495.5,
                    "high": 2500.0,
                    "low": 2475.0,
                    "volume": 14500000
                },
                ...
            ]
        }
    """
    symbol = event.get('symbol')
    start_date_str = event.get('start_date')
    end_date_str = event.get('end_date')
    
    if not symbol or not start_date_str or not end_date_str:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing symbol, start_date, or end_date'})
        }
    
    # Parse dates
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    if (end_date - start_date).days > 31:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Date range cannot exceed 31 days'})
        }
    
    # Collect data for each day in range
    data = []
    current_date = start_date
    
    while current_date <= end_date:
        records = read_csv_from_s3(symbol, current_date.year, current_date.month, current_date.day)
        
        if records:
            stats = calculate_stats(records)
            
            data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'open': stats['open'],
                'close': stats['close'],
                'high': stats['high'],
                'low': stats['low'],
                'volume': stats['volume'],
                'price_change_pct': stats['price_change_pct']
            })
        
        current_date += timedelta(days=1)
    
    result = {
        'symbol': symbol,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'data': data,
        'num_days': len(data)
    }
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }


def top_movers(event: Dict) -> Dict:
    """
    Get top gainers/losers for a specific date
    
    Input:
        {
            "date": "2025-10-07",
            "limit": 10
        }
    
    Output:
        {
            "date": "2025-10-07",
            "gainers": [
                {"symbol": "RELIANCE", "price_change_pct": 2.5},
                ...
            ],
            "losers": [
                {"symbol": "TCS", "price_change_pct": -1.8},
                ...
            ]
        }
    """
    date_str = event.get('date')
    limit = event.get('limit', 10)
    
    if not date_str:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing date'})
        }
    
    # Get daily summary (reuse function)
    summary_response = daily_summary({'date': date_str})
    
    if summary_response['statusCode'] != 200:
        return summary_response
    
    summary_data = json.loads(summary_response['body'])
    symbols = summary_data['summary']
    
    # Sort by price change percentage
    gainers = sorted(symbols, key=lambda x: x['price_change_pct'], reverse=True)[:limit]
    losers = sorted(symbols, key=lambda x: x['price_change_pct'])[:limit]
    
    result = {
        'date': date_str,
        'gainers': [
            {
                'symbol': s['symbol'],
                'price_change_pct': s['price_change_pct'],
                'close': s['close'],
                'volume': s['volume']
            }
            for s in gainers
        ],
        'losers': [
            {
                'symbol': s['symbol'],
                'price_change_pct': s['price_change_pct'],
                'close': s['close'],
                'volume': s['volume']
            }
            for s in losers
        ]
    }
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }


if __name__ == '__main__':
    # Test locally
    test_event = {
        'query_type': 'symbol_stats',
        'symbol': 'RELIANCE',
        'date': '2025-10-07'
    }
    
    response = lambda_handler(test_event, None)
    print(json.dumps(json.loads(response['body']), indent=2))
