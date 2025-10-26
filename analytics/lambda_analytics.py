"""
AWS Lambda Analytics Function for Stock OHLCV Data
Uses Pandas to query CSV files from S3 - 100% FREE TIER

Query Types:
1. symbol_stats - Get statistics for a single symbol on a date
2. daily_summary - Get summary for all symbols on a date
3. date_range - Get data for a symbol over date range
4. top_movers - Get top gainers/losers for a date
"""

import json
import boto3
import pandas as pd
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

# Initialize S3 client
s3_client = boto3.client('s3')

# Get bucket from environment
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'stock-pipeline-mvp')
CSV_PREFIX = 'analytics/csv'


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


def read_csv_from_s3(symbol: str, year: int, month: int, day: int) -> Optional[pd.DataFrame]:
    """
    Read CSV file from S3 for a specific symbol and date
    
    Returns None if file doesn't exist
    """
    try:
        # Construct S3 key with partitioning
        key = f'{CSV_PREFIX}/symbol={symbol}/year={year}/month={month:02d}/day={day:02d}/data.csv.gz'
        
        print(f"Reading s3://{BUCKET_NAME}/{key}")
        
        # Get object from S3
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        
        # Read CSV with gzip compression
        df = pd.read_csv(
            io.BytesIO(response['Body'].read()),
            compression='gzip'
        )
        
        return df
    
    except s3_client.exceptions.NoSuchKey:
        print(f"File not found: s3://{BUCKET_NAME}/{key}")
        return None
    except Exception as e:
        print(f"Error reading CSV: {str(e)}")
        raise


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
    df = read_csv_from_s3(symbol, dt.year, dt.month, dt.day)
    
    if df is None or df.empty:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': f'No data found for {symbol} on {date_str}'})
        }
    
    # Calculate statistics
    first_open = df['open'].iloc[0]
    last_close = df['close'].iloc[-1]
    price_change = last_close - first_open
    price_change_pct = (price_change / first_open) * 100
    
    stats = {
        'symbol': symbol,
        'date': date_str,
        'stats': {
            'open': float(first_open),
            'close': float(last_close),
            'high': float(df['high'].max()),
            'low': float(df['low'].min()),
            'volume': int(df['volume'].sum()),
            'avg_price': float(df['close'].mean()),
            'price_change': float(price_change),
            'price_change_pct': float(price_change_pct),
            'num_records': len(df)
        }
    }
    
    return {
        'statusCode': 200,
        'body': json.dumps(stats)
    }


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
    
    # List all symbols for this date by scanning S3 prefix
    prefix = f'{CSV_PREFIX}/symbol='
    
    try:
        # List all symbol partitions
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=prefix,
            Delimiter='/'
        )
        
        if 'CommonPrefixes' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': f'No data found for {date_str}'})
            }
        
        symbols = []
        for obj in response['CommonPrefixes']:
            # Extract symbol from prefix (e.g., 'analytics/csv/symbol=RELIANCE/' -> 'RELIANCE')
            symbol = obj['Prefix'].split('symbol=')[1].rstrip('/')
            symbols.append(symbol)
        
        # Get stats for each symbol
        summary = []
        for symbol in symbols:
            df = read_csv_from_s3(symbol, dt.year, dt.month, dt.day)
            
            if df is not None and not df.empty:
                first_open = df['open'].iloc[0]
                last_close = df['close'].iloc[-1]
                price_change_pct = ((last_close - first_open) / first_open) * 100
                
                summary.append({
                    'symbol': symbol,
                    'open': float(first_open),
                    'close': float(last_close),
                    'high': float(df['high'].max()),
                    'low': float(df['low'].min()),
                    'volume': int(df['volume'].sum()),
                    'price_change_pct': float(price_change_pct)
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
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
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
        df = read_csv_from_s3(symbol, current_date.year, current_date.month, current_date.day)
        
        if df is not None and not df.empty:
            first_open = df['open'].iloc[0]
            last_close = df['close'].iloc[-1]
            
            data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'open': float(first_open),
                'close': float(last_close),
                'high': float(df['high'].max()),
                'low': float(df['low'].min()),
                'volume': int(df['volume'].sum()),
                'price_change_pct': float(((last_close - first_open) / first_open) * 100)
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
