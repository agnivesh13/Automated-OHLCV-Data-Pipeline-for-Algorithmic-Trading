#!/usr/bin/env python3
"""
API Handler Lambda Function for Stock Data Service
Provides REST API endpoints for other teams to consume OHLCV data
"""

import json
import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Main Lambda handler for API Gateway requests
    """
    try:
        # Extract request information
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}
        
        logger.info(f"📡 API Request: {http_method} {path}")
        logger.info(f"🔍 Query params: {query_parameters}")
        logger.info(f"📍 Path params: {path_parameters}")
        
        # Route to appropriate handler
        if path.startswith('/symbols'):
            return handle_symbols(query_parameters)
        elif path.startswith('/ohlcv/'):
            symbol = path_parameters.get('symbol')
            return handle_ohlcv(symbol, query_parameters)
        elif path.startswith('/latest'):
            return handle_latest(query_parameters)
        elif path.startswith('/historical'):
            return handle_historical(query_parameters)
        elif path.startswith('/alfaquantz/price/get'):
            # Support both path-style and query-style:
            # Path: /alfaquantz/price/get/infy,1d,3m
            # Query: /alfaquantz/price/get?symbol=infy&interval=1d&period=3m
            return handle_alfa_price(path, query_parameters)
        else:
            return create_response(404, {
                'error': 'Endpoint not found',
                'available_endpoints': {
                    '/symbols': 'List all available symbols',
                    '/ohlcv/{symbol}': 'Get OHLCV data for specific symbol',
                    '/latest': 'Get latest data for symbols',
                    '/historical': 'Get historical data'
                }
            })
            
    except Exception as e:
        logger.error(f"❌ API Error: {str(e)}")
        return create_response(500, {
            'error': 'Internal server error',
            'message': str(e)
        })

def handle_symbols(query_params: Dict) -> Dict:
    """
    GET /symbols - List all available symbols
    Query params:
    - limit: int (optional) - Limit number of symbols returned
    """
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.environ['S3_BUCKET_NAME']
        
        # Get list of unique symbols from S3 files
        symbols = get_available_symbols(s3_client, bucket_name)
        
        # Apply limit if specified
        limit = query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
                symbols = symbols[:limit]
            except ValueError:
                return create_response(400, {
                    'error': 'Invalid limit parameter',
                    'message': 'Limit must be a valid integer'
                })
        
        return create_response(200, {
            'symbols': symbols,
            'count': len(symbols),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        logger.error(f"❌ Error in handle_symbols: {str(e)}")
        return create_response(500, {
            'error': 'Failed to retrieve symbols',
            'message': str(e)
        })

def handle_ohlcv(symbol: str, query_params: Dict) -> Dict:
    """
    GET /ohlcv/{symbol} - Get OHLCV data for specific symbol
    Query params:
    - from: str (optional) - Start date (YYYY-MM-DD)
    - to: str (optional) - End date (YYYY-MM-DD)
    - interval: str (optional) - Time interval (5, 15, 30, 60 minutes)
    - limit: int (optional) - Limit number of candles returned
    """
    try:
        if not symbol:
            return create_response(400, {
                'error': 'Missing symbol parameter',
                'message': 'Symbol is required in the path: /ohlcv/{symbol}'
            })
        
        # Normalize symbol format
        symbol = normalize_symbol(symbol)
        
        s3_client = boto3.client('s3')
        bucket_name = os.environ['S3_BUCKET_NAME']
        
        # Parse date parameters
        from_date = query_params.get('from')
        to_date = query_params.get('to')
        interval = query_params.get('interval', '5')  # Default 5-minute
        limit = query_params.get('limit')
        
        # Get OHLCV data for symbol
        ohlcv_data = get_ohlcv_data(
            s3_client, bucket_name, symbol, 
            from_date, to_date, interval, limit
        )
        
        if not ohlcv_data:
            return create_response(404, {
                'error': 'No data found',
                'message': f'No OHLCV data found for symbol {symbol}',
                'symbol': symbol
            })
        
        return create_response(200, {
            'symbol': symbol,
            'interval': interval,
            'data': ohlcv_data,
            'count': len(ohlcv_data),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        logger.error(f"❌ Error in handle_ohlcv: {str(e)}")
        return create_response(500, {
            'error': 'Failed to retrieve OHLCV data',
            'message': str(e),
            'symbol': symbol
        })

def handle_latest(query_params: Dict) -> Dict:
    """
    GET /latest - Get latest data for all or specified symbols
    Query params:
    - symbols: str (optional) - Comma-separated list of symbols
    """
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.environ['S3_BUCKET_NAME']
        
        # Parse symbols parameter
        symbols_param = query_params.get('symbols')
        if symbols_param:
            symbols = [normalize_symbol(s.strip()) for s in symbols_param.split(',')]
        else:
            symbols = get_available_symbols(s3_client, bucket_name)[:10]  # Limit to 10 for performance
        
        # Get latest data for symbols
        latest_data = get_latest_data(s3_client, bucket_name, symbols)
        
        return create_response(200, {
            'symbols': symbols,
            'data': latest_data,
            'count': len(latest_data),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        logger.error(f"❌ Error in handle_latest: {str(e)}")
        return create_response(500, {
            'error': 'Failed to retrieve latest data',
            'message': str(e)
        })

def handle_historical(query_params: Dict) -> Dict:
    """
    GET /historical - Get bulk historical data
    Query params:
    - symbol: str (optional) - Single symbol
    - symbols: str (optional) - Comma-separated list of symbols  
    - from: str (optional) - Start date (YYYY-MM-DD)
    - to: str (optional) - End date (YYYY-MM-DD)
    - format: str (optional) - Response format ('json', 'csv')
    """
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.environ['S3_BUCKET_NAME']
        
        # Parse parameters
        symbol = query_params.get('symbol')
        symbols_param = query_params.get('symbols')
        from_date = query_params.get('from')
        to_date = query_params.get('to')
        format_type = query_params.get('format', 'json')
        
        # Determine symbols to fetch
        if symbol:
            symbols = [normalize_symbol(symbol)]
        elif symbols_param:
            symbols = [normalize_symbol(s.strip()) for s in symbols_param.split(',')]
        else:
            symbols = get_available_symbols(s3_client, bucket_name)[:5]  # Limit for performance
        
        # Get historical data
        historical_data = get_historical_data(
            s3_client, bucket_name, symbols, from_date, to_date
        )
        
        if format_type.lower() == 'csv':
            # Convert to CSV format
            csv_data = convert_to_csv(historical_data)
            return create_response(200, csv_data, content_type='text/csv')
        
        return create_response(200, {
            'symbols': symbols,
            'from_date': from_date,
            'to_date': to_date,
            'data': historical_data,
            'total_records': sum(len(data.get('candles', [])) for data in historical_data.values()),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        logger.error(f"❌ Error in handle_historical: {str(e)}")
        return create_response(500, {
            'error': 'Failed to retrieve historical data',
            'message': str(e)
        })

def get_available_symbols(s3_client, bucket_name: str) -> List[str]:
    """
    Get list of available symbols from S3 data
    """
    try:
        # Get the latest file to extract symbol list
        latest_file_key = get_latest_file_key(s3_client, bucket_name)
        if not latest_file_key:
            return []
        
        # Read the latest file
        response = s3_client.get_object(Bucket=bucket_name, Key=latest_file_key)
        data = json.loads(response['Body'].read().decode('utf-8'))
        
        # Extract symbols from data structure
        symbols = []
        if 'data' in data and isinstance(data['data'], dict):
            # Old format
            symbols = list(data['data'].keys())
        else:
            # New format - symbols are direct keys
            symbols = [k for k in data.keys() if k != 'metadata']
        
        # Normalize symbol names
        symbols = [normalize_symbol(symbol) for symbol in symbols if symbol]
        return sorted(symbols)
        
    except Exception as e:
        logger.error(f"❌ Error getting available symbols: {str(e)}")
        return []

def get_latest_file_key(s3_client, bucket_name: str) -> Optional[str]:
    """
    Get the key of the most recent data file
    """
    try:
        raw_prefix = os.environ.get('S3_RAW_PREFIX', 'Raw data/Prices/')
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=raw_prefix,
            MaxKeys=1000
        )
        
        if 'Contents' not in response:
            return None
        
        # Sort by last modified and get the latest
        files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
        return files[0]['Key'] if files else None
        
    except Exception as e:
        logger.error(f"❌ Error getting latest file: {str(e)}")
        return None

def parse_date_to_timestamp(date_str: str, is_start: bool = True) -> int:
    """
    Convert date string (YYYY-MM-DD) to Unix timestamp
    Args:
        date_str: Date in YYYY-MM-DD format
        is_start: True for start of day (00:00:00), False for end of day (23:59:59)
    """
    try:
        if not date_str:
            return 0
        
        # Parse date string
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        if is_start:
            # Start of day (00:00:00)
            return int(date_obj.timestamp())
        else:
            # End of day (23:59:59)
            end_of_day = date_obj.replace(hour=23, minute=59, second=59)
            return int(end_of_day.timestamp())
    except Exception as e:
        logger.warning(f"⚠️ Error parsing date '{date_str}': {str(e)}")
        return 0

def calculate_days_between(from_date: str = None, to_date: str = None) -> int:
    """
    Calculate number of days between from_date and to_date
    Defaults to reasonable values if dates not provided
    """
    try:
        if not from_date and not to_date:
            return 7  # Default to 7 days
        
        # Parse dates
        if to_date:
            to_dt = datetime.strptime(to_date, '%Y-%m-%d')
        else:
            to_dt = datetime.utcnow()
        
        if from_date:
            from_dt = datetime.strptime(from_date, '%Y-%m-%d')
        else:
            from_dt = to_dt - timedelta(days=7)
        
        # Calculate difference
        days = (to_dt - from_dt).days + 1  # +1 to include both endpoints
        
        # Cap at reasonable limits
        return min(max(days, 1), 365)  # Between 1 and 365 days
        
    except Exception as e:
        logger.warning(f"⚠️ Error calculating days between dates: {str(e)}")
        return 7  # Default fallback

def get_ohlcv_data(s3_client, bucket_name: str, symbol: str, 
                   from_date: str = None, to_date: str = None, 
                   interval: str = '5', limit: str = None) -> List[Dict]:
    """
    Get OHLCV data for a specific symbol with date range filtering
    """
    try:
        # Determine how many days of files to fetch based on date range
        days_to_fetch = 7  # Default
        if from_date or to_date:
            days_to_fetch = calculate_days_between(from_date, to_date)
        
        recent_files = get_recent_files(s3_client, bucket_name, days=max(days_to_fetch, 7))
        ohlcv_candles = []
        
        for file_key in recent_files:
            try:
                response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
                data = json.loads(response['Body'].read().decode('utf-8'))
                
                # Find symbol data
                symbol_data = None
                if 'data' in data and isinstance(data['data'], dict):
                    symbol_data = data['data'].get(symbol)
                else:
                    symbol_data = data.get(symbol)
                
                if symbol_data and 'candles' in symbol_data:
                    candles = symbol_data['candles']
                    
                    # Convert candle format
                    for candle in candles:
                        if isinstance(candle, list) and len(candle) >= 6:
                            ohlcv_candles.append({
                                'timestamp': candle[0],
                                'datetime': datetime.fromtimestamp(candle[0]).isoformat() + 'Z',
                                'open': candle[1],
                                'high': candle[2],
                                'low': candle[3],
                                'close': candle[4],
                                'volume': candle[5]
                            })
                        elif isinstance(candle, dict):
                            # Already in dict format
                            ohlcv_candles.append({
                                'timestamp': candle.get('timestamp'),
                                'datetime': datetime.fromtimestamp(candle.get('timestamp', 0)).isoformat() + 'Z',
                                'open': candle.get('open'),
                                'high': candle.get('high'),
                                'low': candle.get('low'),
                                'close': candle.get('close'),
                                'volume': candle.get('volume')
                            })
                            
            except Exception as e:
                logger.warning(f"⚠️ Error processing file {file_key}: {str(e)}")
                continue
        
        # Remove duplicates and sort by timestamp
        unique_candles = {}
        for candle in ohlcv_candles:
            timestamp = candle.get('timestamp')
            if timestamp:
                unique_candles[timestamp] = candle
        
        sorted_candles = sorted(unique_candles.values(), key=lambda x: x.get('timestamp', 0))
        
        # Apply date range filtering
        if from_date or to_date:
            from_ts = parse_date_to_timestamp(from_date, is_start=True) if from_date else 0
            to_ts = parse_date_to_timestamp(to_date, is_start=False) if to_date else float('inf')
            
            sorted_candles = [
                c for c in sorted_candles 
                if from_ts <= c.get('timestamp', 0) <= to_ts
            ]
        
        # Apply limit if specified
        if limit:
            try:
                limit_int = int(limit)
                sorted_candles = sorted_candles[-limit_int:]  # Get most recent
            except ValueError:
                pass  # Ignore invalid limit
        
        return sorted_candles
        
    except Exception as e:
        logger.error(f"❌ Error getting OHLCV data for {symbol}: {str(e)}")
        return []

def get_recent_files(s3_client, bucket_name: str, days: int = 7) -> List[str]:
    """
    Get list of recent file keys
    """
    try:
        raw_prefix = os.environ.get('S3_RAW_PREFIX', 'Raw data/Prices/')
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=raw_prefix,
            MaxKeys=1000
        )
        
        if 'Contents' not in response:
            return []
        
        # Filter files from last N days
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_files = [
            obj['Key'] for obj in response['Contents']
            if obj['LastModified'].replace(tzinfo=None) >= cutoff_date
        ]
        
        return sorted(recent_files, key=lambda x: x, reverse=True)[:50]  # Limit processing
        
    except Exception as e:
        logger.error(f"❌ Error getting recent files: {str(e)}")
        return []

def get_latest_data(s3_client, bucket_name: str, symbols: List[str]) -> Dict:
    """
    Get latest data for specified symbols
    """
    try:
        latest_file_key = get_latest_file_key(s3_client, bucket_name)
        if not latest_file_key:
            return {}
        
        response = s3_client.get_object(Bucket=bucket_name, Key=latest_file_key)
        data = json.loads(response['Body'].read().decode('utf-8'))
        
        latest_data = {}
        
        for symbol in symbols:
            symbol_data = None
            if 'data' in data and isinstance(data['data'], dict):
                symbol_data = data['data'].get(symbol)
            else:
                symbol_data = data.get(symbol)
            
            if symbol_data:
                latest_data[symbol] = {
                    'symbol': symbol,
                    'latest_price': symbol_data.get('latest_price'),
                    'total_candles': symbol_data.get('total_candles'),
                    'resolution': symbol_data.get('resolution'),
                    'timestamp': symbol_data.get('timestamp'),
                    'last_candle': symbol_data.get('candles', [])[-1] if symbol_data.get('candles') else None
                }
        
        return latest_data
        
    except Exception as e:
        logger.error(f"❌ Error getting latest data: {str(e)}")
        return {}

def get_historical_data(s3_client, bucket_name: str, symbols: List[str], 
                       from_date: str = None, to_date: str = None) -> Dict:
    """
    Get historical data for specified symbols with date range filtering
    """
    try:
        # Determine how many days of files to fetch based on date range
        days_to_fetch = 30  # Default
        if from_date or to_date:
            days_to_fetch = calculate_days_between(from_date, to_date)
        
        recent_files = get_recent_files(s3_client, bucket_name, days=max(days_to_fetch, 7))
        historical_data = {}
        
        for symbol in symbols:
            historical_data[symbol] = {
                'symbol': symbol,
                'candles': []
            }
        
        # Process files
        for file_key in recent_files[:20]:  # Limit processing for performance
            try:
                response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
                data = json.loads(response['Body'].read().decode('utf-8'))
                
                for symbol in symbols:
                    symbol_data = None
                    if 'data' in data and isinstance(data['data'], dict):
                        symbol_data = data['data'].get(symbol)
                    else:
                        symbol_data = data.get(symbol)
                    
                    if symbol_data and 'candles' in symbol_data:
                        historical_data[symbol]['candles'].extend(symbol_data['candles'])
                        
            except Exception as e:
                logger.warning(f"⚠️ Error processing file {file_key}: {str(e)}")
                continue
        
        # Deduplicate and sort candles for each symbol
        # Parse date range for filtering
        from_ts = parse_date_to_timestamp(from_date, is_start=True) if from_date else 0
        to_ts = parse_date_to_timestamp(to_date, is_start=False) if to_date else float('inf')
        
        for symbol in historical_data:
            candles = historical_data[symbol]['candles']
            unique_candles = {}
            
            for candle in candles:
                if isinstance(candle, list) and len(candle) >= 6:
                    timestamp = candle[0]
                    # Apply date filtering
                    if from_ts <= timestamp <= to_ts:
                        unique_candles[timestamp] = {
                            'timestamp': timestamp,
                            'datetime': datetime.fromtimestamp(timestamp).isoformat() + 'Z',
                            'open': candle[1],
                            'high': candle[2],
                            'low': candle[3],
                            'close': candle[4],
                            'volume': candle[5]
                        }
            
            historical_data[symbol]['candles'] = sorted(
                unique_candles.values(), 
                key=lambda x: x['timestamp']
            )
            historical_data[symbol]['count'] = len(historical_data[symbol]['candles'])
        
        return historical_data
        
    except Exception as e:
        logger.error(f"❌ Error getting historical data: {str(e)}")
        return {}

def normalize_symbol(symbol: str) -> str:
    """
    Normalize symbol format (e.g., ensure NSE:SYMBOL-EQ format)
    """
    if not symbol:
        return symbol
    
    symbol = symbol.upper().strip()
    
    # If it's already in NSE:SYMBOL-EQ format, return as is
    if ':' in symbol and '-EQ' in symbol:
        return symbol
    
    # If it's just the symbol name, add NSE: prefix and -EQ suffix
    if ':' not in symbol:
        if not symbol.endswith('-EQ'):
            symbol = f"NSE:{symbol}-EQ"
        else:
            symbol = f"NSE:{symbol}"
    
    return symbol

def convert_to_csv(data: Dict) -> str:
    """
    Convert historical data to CSV format
    """
    try:
        csv_lines = ["symbol,timestamp,datetime,open,high,low,close,volume"]
        
        for symbol, symbol_data in data.items():
            candles = symbol_data.get('candles', [])
            for candle in candles:
                line = f"{symbol},{candle['timestamp']},{candle['datetime']},{candle['open']},{candle['high']},{candle['low']},{candle['close']},{candle['volume']}"
                csv_lines.append(line)
        
        return "\n".join(csv_lines)
        
    except Exception as e:
        logger.error(f"❌ Error converting to CSV: {str(e)}")
        return ""

def create_response(status_code: int, body: any, content_type: str = 'application/json') -> Dict:
    """
    Create standardized API Gateway response
    """
    headers = {
        'Content-Type': content_type,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,OPTIONS'
    }
    
    if content_type == 'application/json':
        body = json.dumps(body, indent=2)
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': body
    }


def handle_alfa_price(path: str, query_params: Dict = None) -> Dict:
    """
    Handle endpoints like /alfaquantz/price/get/{symbol},{interval},{period}
    where period is e.g. 3m (3 months), 2y (2 years), 30d (30 days)
    """
    try:
        # Prefer query parameters if present
        qp = query_params or {}
        raw_symbol = qp.get('symbol')
        interval = qp.get('interval')
        period = qp.get('period')

        if not raw_symbol or not interval or not period:
            # Fallback to path-style parsing
            prefix = '/alfaquantz/price/get/'
            tail = path[len(prefix):].strip('/')
            if not tail:
                return create_response(400, {'error': 'Missing parameters. Expected /alfaquantz/price/get/{symbol},{interval},{period} or query params'})

            parts = [p.strip() for p in tail.split(',') if p.strip()]
            if len(parts) < 3:
                return create_response(400, {'error': 'Invalid parameters. Expected format: symbol,interval,period'})

            raw_symbol, interval, period = parts[0], parts[1], parts[2]
        symbol = normalize_symbol(raw_symbol)

        s3_client = boto3.client('s3')
        bucket_name = os.environ.get('S3_BUCKET_NAME')

        # Convert period to from_date (YYYY-MM-DD) and to_date (today)
        to_date = datetime.utcnow().date()
        from_date = period_to_from_date(period, to_date)

        # Fetch historical data (MVP uses recent files; we'll filter by date)
        historical = get_historical_data(s3_client, bucket_name, [symbol], from_date.isoformat(), to_date.isoformat())

        # historical is a dict keyed by symbol
        symbol_data = historical.get(symbol, {'candles': []})

        # Filter candles by from_date (convert to timestamp)
        try:
            from_ts = int(datetime.combine(from_date, datetime.min.time()).timestamp())
        except Exception:
            from_ts = 0

        raw_candles = []
        for c in symbol_data.get('candles', []):
            # normalize to list form: [ts, open, high, low, close, volume]
            if isinstance(c, list) and len(c) >= 6:
                ts = int(c[0])
                if ts >= from_ts:
                    raw_candles.append([ts, float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])])
            elif isinstance(c, dict):
                ts = int(c.get('timestamp', 0) or 0)
                if ts >= from_ts:
                    raw_candles.append([
                        ts,
                        float(c.get('open', 0) or 0),
                        float(c.get('high', 0) or 0),
                        float(c.get('low', 0) or 0),
                        float(c.get('close', 0) or 0),
                        float(c.get('volume', 0) or 0)
                    ])

        # If interval aggregation requested, aggregate from raw (assumed smaller) candles
        try:
            target_minutes = parse_interval_to_minutes(interval)
        except Exception:
            target_minutes = None

        aggregated = raw_candles
        if target_minutes and target_minutes > 0:
            # If target is larger than raw granularity, aggregate
            aggregated = aggregate_candles(raw_candles, target_minutes)

        return create_response(200, {
            'symbol_requested': raw_symbol,
            'symbol_normalized': symbol,
            'interval': interval,
            'period': period,
            'from_date': from_date.isoformat(),
            'to_date': to_date.isoformat(),
            'count': len(aggregated),
            'candles': aggregated,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })

    except Exception as e:
        logger.error(f"❌ Error in handle_alfa_price: {e}")
        return create_response(500, {'error': 'Failed to process alfaquantz price request', 'message': str(e)})


def period_to_from_date(period: str, to_date) -> datetime.date:
    """
    Convert period token like '3m', '2y', '30d' into a from_date (datetime.date).
    For simplicity months are approximated as 30 days and years as 365 days.
    """
    try:
        token = period.lower().strip()
        unit = token[-1]
        value = int(token[:-1]) if len(token) > 1 else 0
        days = 0
        if unit == 'd':
            days = value
        elif unit == 'm':
            days = value * 30
        elif unit == 'y':
            days = value * 365
        else:
            # Default assume days
            days = int(token)

        return to_date - timedelta(days=days)
    except Exception:
        # On parse error default to 30 days
        return to_date - timedelta(days=30)


def parse_interval_to_minutes(interval: str) -> int:
    """
    Parse interval tokens like '5m', '15m', '1d' into minutes.
    Returns minutes as int. '1d' -> 1440.
    """
    token = interval.lower().strip()
    if token.endswith('m'):
        return int(token[:-1])
    if token.endswith('h'):
        return int(token[:-1]) * 60
    if token.endswith('d'):
        return int(token[:-1]) * 1440
    # fallback: assume minutes
    return int(token)


def aggregate_candles(candles: List[List], target_minutes: int) -> List[List]:
    """
    Aggregate list-of-list candles into target interval (minutes).
    Input candles expected as [ts, open, high, low, close, volume] with ts in seconds.
    Output uses same list form, ordered by timestamp ascending.
    """
    if not candles:
        return []

    # Sort by timestamp
    candles_sorted = sorted(candles, key=lambda x: x[0])

    bucket_seconds = target_minutes * 60
    buckets = {}

    for c in candles_sorted:
        ts, o, h, l, cl, vol = c[0], c[1], c[2], c[3], c[4], c[5]
        # bucket start timestamp (aligned to epoch)
        bucket_start = (ts // bucket_seconds) * bucket_seconds
        if bucket_start not in buckets:
            buckets[bucket_start] = {
                'opens': [],
                'closes': [],
                'high': h,
                'low': l,
                'volume': 0
            }
        b = buckets[bucket_start]
        b['opens'].append((ts, o))
        b['closes'].append((ts, cl))
        b['high'] = max(b['high'], h)
        b['low'] = min(b['low'], l)
        b['volume'] += vol

    # Build aggregated list sorted by bucket timestamp
    aggregated = []
    for bs in sorted(buckets.keys()):
        b = buckets[bs]
        # open is the open of the earliest ts in opens
        open_val = sorted(b['opens'], key=lambda x: x[0])[0][1]
        close_val = sorted(b['closes'], key=lambda x: x[0])[-1][1]
        high_val = b['high']
        low_val = b['low']
        vol_val = b['volume']
        aggregated.append([bs, open_val, high_val, low_val, close_val, vol_val])

    return aggregated
