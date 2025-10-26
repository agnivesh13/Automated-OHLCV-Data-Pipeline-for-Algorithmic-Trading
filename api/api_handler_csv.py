#!/usr/bin/env python3
"""
Enhanced API Handler that works with aggregated CSV files in S3
Supports querying partitioned CSV data by date range
"""

import json
import boto3
import logging
import gzip
import io
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class CSVDataReader:
    """Read aggregated CSV files from S3 partitions"""
    
    def __init__(self, bucket_name: str, csv_prefix: str = "analytics/csv/"):
        self.bucket_name = bucket_name
        self.csv_prefix = csv_prefix
        self.s3_client = boto3.client('s3')
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols from CSV partitions"""
        try:
            # List all symbol partitions
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.csv_prefix,
                Delimiter='/'
            )
            
            symbols = []
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    # Extract symbol from prefix like "analytics/csv/symbol=RELIANCE/"
                    symbol_prefix = prefix['Prefix']
                    if 'symbol=' in symbol_prefix:
                        symbol = symbol_prefix.split('symbol=')[1].strip('/')
                        symbols.append(symbol)
            
            return sorted(symbols)
            
        except Exception as e:
            logger.error(f"Error getting available symbols: {e}")
            return []
    
    def list_csv_files_for_date_range(self, symbol: str, from_date: str, to_date: str) -> List[str]:
        """
        List CSV files for symbol within date range
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE')
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
        
        Returns:
            List of S3 keys for CSV files
        """
        try:
            from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            to_dt = datetime.strptime(to_date, '%Y-%m-%d')
            
            csv_files = []
            current_dt = from_dt
            
            # Iterate through each day in range
            while current_dt <= to_dt:
                year = current_dt.year
                month = current_dt.month
                day = current_dt.day
                
                # Build S3 prefix for this date partition
                prefix = f"{self.csv_prefix}symbol={symbol}/year={year}/month={month:02d}/day={day:02d}/"
                
                logger.info(f"Searching partition: {prefix}")
                
                try:
                    response = self.s3_client.list_objects_v2(
                        Bucket=self.bucket_name,
                        Prefix=prefix
                    )
                    
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            key = obj['Key']
                            # Only include actual data files
                            if key.endswith('.csv') or key.endswith('.csv.gz'):
                                csv_files.append(key)
                                logger.info(f"Found file: {key}")
                
                except Exception as e:
                    logger.warning(f"Error listing partition {prefix}: {e}")
                
                current_dt += timedelta(days=1)
            
            return csv_files
            
        except Exception as e:
            logger.error(f"Error listing CSV files: {e}")
            return []
    
    def read_csv_file(self, s3_key: str) -> List[Dict]:
        """Read a CSV file from S3 and return records"""
        try:
            logger.info(f"Reading CSV file: {s3_key}")
            
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read()
            
            # Decompress if gzipped
            if s3_key.endswith('.gz'):
                content = gzip.decompress(content)
            
            # Parse CSV
            csv_text = content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_text))
            
            records = list(csv_reader)
            logger.info(f"Read {len(records)} records from {s3_key}")
            
            return records
            
        except Exception as e:
            logger.error(f"Error reading CSV file {s3_key}: {e}")
            return []
    
    def get_data_for_symbol(self, symbol: str, from_date: str, to_date: str, 
                           limit: Optional[int] = None) -> Dict:
        """
        Get aggregated data for a symbol within date range
        
        Args:
            symbol: Stock symbol
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            limit: Optional limit on number of candles returned
        
        Returns:
            Dictionary with symbol data and candles
        """
        try:
            # List all CSV files for this symbol in date range
            csv_files = self.list_csv_files_for_date_range(symbol, from_date, to_date)
            
            if not csv_files:
                return {
                    'symbol': symbol,
                    'candles': [],
                    'count': 0,
                    'message': 'No data available for date range'
                }
            
            # Read all CSV files and aggregate
            all_records = []
            for csv_file in csv_files:
                records = self.read_csv_file(csv_file)
                all_records.extend(records)
            
            # Convert to OHLCV candle format
            candles = []
            seen_timestamps = set()  # Deduplicate
            
            for record in all_records:
                try:
                    # CSV uses 'timestamp_unix' and 'timestamp_iso' fields
                    timestamp = record.get('timestamp_unix') or record.get('timestamp')
                    datetime_str = record.get('timestamp_iso') or record.get('datetime')
                    
                    if not timestamp:
                        continue  # Skip records without timestamp
                    
                    # Skip duplicates
                    if timestamp in seen_timestamps:
                        continue
                    seen_timestamps.add(timestamp)
                    
                    candle = {
                        'timestamp': int(timestamp),
                        'datetime': datetime_str,
                        'open': float(record.get('open', 0)),
                        'high': float(record.get('high', 0)),
                        'low': float(record.get('low', 0)),
                        'close': float(record.get('close', 0)),
                        'volume': int(float(record.get('volume', 0)))
                    }
                    candles.append(candle)
                    
                except Exception as e:
                    logger.warning(f"Skipping invalid record: {e}")
                    continue
            
            # Sort by timestamp
            candles.sort(key=lambda x: x['timestamp'])
            
            # Apply limit if specified
            if limit and limit > 0:
                candles = candles[-limit:]  # Return most recent
            
            return {
                'symbol': symbol,
                'candles': candles,
                'count': len(candles),
                'csv_files_processed': len(csv_files),
                'from_date': from_date,
                'to_date': to_date
            }
            
        except Exception as e:
            logger.error(f"Error getting data for symbol {symbol}: {e}")
            return {
                'symbol': symbol,
                'candles': [],
                'count': 0,
                'error': str(e)
            }


def lambda_handler(event, context):
    """
    Enhanced Lambda handler for API Gateway requests with CSV support
    """
    try:
        # Extract request information
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}
        
        logger.info(f"API Request: {http_method} {path}")
        logger.info(f"Query params: {query_parameters}")
        
        # Get environment configuration
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'stock-pipeline-mvp-dev-ohlcv-5e23bf76')
        csv_prefix = os.environ.get('CSV_PREFIX', 'analytics/csv/')
        
        # Initialize CSV reader
        csv_reader = CSVDataReader(bucket_name, csv_prefix)
        
        # Route to appropriate handler
        if path.startswith('/symbols'):
            return handle_symbols_csv(csv_reader, query_parameters)
        elif path.startswith('/ohlcv/'):
            symbol = path_parameters.get('symbol')
            return handle_ohlcv_csv(csv_reader, symbol, query_parameters)
        elif path.startswith('/latest'):
            return handle_latest_csv(csv_reader, query_parameters)
        elif path.startswith('/historical'):
            return handle_historical_csv(csv_reader, query_parameters)
        else:
            return create_response(404, {
                'error': 'Endpoint not found',
                'available_endpoints': {
                    '/symbols': 'List all available symbols',
                    '/ohlcv/{symbol}': 'Get OHLCV data for specific symbol',
                    '/latest': 'Get latest data for symbols',
                    '/historical': 'Get historical data with date range'
                }
            })
            
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        return create_response(500, {
            'error': 'Internal server error',
            'message': str(e)
        })


def handle_symbols_csv(csv_reader: CSVDataReader, query_params: Dict) -> Dict:
    """GET /symbols - List all available symbols from CSV partitions"""
    try:
        symbols = csv_reader.get_available_symbols()
        
        # Apply limit if specified
        limit = query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
                symbols = symbols[:limit]
            except ValueError:
                return create_response(400, {
                    'error': 'Invalid limit parameter'
                })
        
        return create_response(200, {
            'symbols': symbols,
            'count': len(symbols),
            'data_source': 'csv_partitions',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        logger.error(f"Error in handle_symbols_csv: {str(e)}")
        return create_response(500, {
            'error': 'Failed to retrieve symbols',
            'message': str(e)
        })


def handle_ohlcv_csv(csv_reader: CSVDataReader, symbol: str, query_params: Dict) -> Dict:
    """GET /ohlcv/{symbol} - Get OHLCV data from CSV partitions"""
    try:
        if not symbol:
            return create_response(400, {
                'error': 'Missing symbol parameter'
            })
        
        symbol = symbol.upper()
        
        # Parse date parameters
        from_date = query_params.get('from')
        to_date = query_params.get('to')
        limit = query_params.get('limit')
        
        # Default to last 7 days if no dates specified
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        if not from_date:
            from_dt = datetime.now() - timedelta(days=7)
            from_date = from_dt.strftime('%Y-%m-%d')
        
        # Parse limit
        limit_int = None
        if limit:
            try:
                limit_int = int(limit)
            except ValueError:
                pass
        
        # Get data from CSV partitions
        data = csv_reader.get_data_for_symbol(symbol, from_date, to_date, limit_int)
        
        if data['count'] == 0:
            return create_response(404, {
                'error': 'No data found',
                'message': f'No data found for {symbol} between {from_date} and {to_date}',
                'symbol': symbol,
                'from_date': from_date,
                'to_date': to_date
            })
        
        return create_response(200, {
            'symbol': symbol,
            'from_date': from_date,
            'to_date': to_date,
            'data': data['candles'],
            'count': data['count'],
            'data_source': 'csv_partitions',
            'csv_files_processed': data.get('csv_files_processed', 0),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        logger.error(f"Error in handle_ohlcv_csv: {str(e)}")
        return create_response(500, {
            'error': 'Failed to retrieve OHLCV data',
            'message': str(e)
        })


def handle_latest_csv(csv_reader: CSVDataReader, query_params: Dict) -> Dict:
    """GET /latest - Get latest data from CSV partitions"""
    try:
        # Parse symbols parameter
        symbols_param = query_params.get('symbols')
        if symbols_param:
            symbols = [s.strip().upper() for s in symbols_param.split(',')]
        else:
            # Get all available symbols, limit to 10
            symbols = csv_reader.get_available_symbols()[:10]
        
        # Get latest data (last 1 day) for each symbol
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        latest_data = {}
        for symbol in symbols:
            data = csv_reader.get_data_for_symbol(symbol, yesterday, today, limit=1)
            if data['count'] > 0:
                latest_candle = data['candles'][-1]
                latest_data[symbol] = {
                    'symbol': symbol,
                    'latest_price': latest_candle['close'],
                    'last_candle': latest_candle,
                    'timestamp': latest_candle['datetime']
                }
        
        return create_response(200, {
            'symbols': symbols,
            'data': latest_data,
            'count': len(latest_data),
            'data_source': 'csv_partitions',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        logger.error(f"Error in handle_latest_csv: {str(e)}")
        return create_response(500, {
            'error': 'Failed to retrieve latest data',
            'message': str(e)
        })


def handle_historical_csv(csv_reader: CSVDataReader, query_params: Dict) -> Dict:
    """GET /historical - Get bulk historical data from CSV partitions"""
    try:
        # Parse parameters
        symbol = query_params.get('symbol')
        symbols_param = query_params.get('symbols')
        from_date = query_params.get('from')
        to_date = query_params.get('to')
        
        # Determine symbols to fetch
        if symbol:
            symbols = [symbol.upper()]
        elif symbols_param:
            symbols = [s.strip().upper() for s in symbols_param.split(',')]
        else:
            symbols = csv_reader.get_available_symbols()[:5]
        
        # Default date range: last 30 days
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        if not from_date:
            from_dt = datetime.now() - timedelta(days=30)
            from_date = from_dt.strftime('%Y-%m-%d')
        
        # Get historical data for all symbols
        historical_data = {}
        total_records = 0
        
        for sym in symbols:
            data = csv_reader.get_data_for_symbol(sym, from_date, to_date)
            historical_data[sym] = data
            total_records += data['count']
        
        return create_response(200, {
            'symbols': symbols,
            'from_date': from_date,
            'to_date': to_date,
            'data': historical_data,
            'total_records': total_records,
            'data_source': 'csv_partitions',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
    except Exception as e:
        logger.error(f"Error in handle_historical_csv: {str(e)}")
        return create_response(500, {
            'error': 'Failed to retrieve historical data',
            'message': str(e)
        })


def create_response(status_code: int, body: any, content_type: str = 'application/json') -> Dict:
    """Create standardized API Gateway response"""
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
