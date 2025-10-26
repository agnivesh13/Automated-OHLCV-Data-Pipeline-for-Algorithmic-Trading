#!/usr/bin/env python3
"""
Lightweight ETL Lambda Function for Stock Price Processing
Avoids heavy libraries like pandas/pyarrow by using native Python + boto3
Converts raw JSON to CSV format for easy Athena querying
"""

import json
import logging
import os
import csv
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from io import StringIO
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class LightweightETL:
    """
    Lightweight ETL processor that converts raw JSON to CSV/Parquet-alternative
    Uses only stdlib + boto3 (no pandas/pyarrow)
    """
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.sns_client = boto3.client('sns')
        
    def normalize_ohlcv_record(self, symbol_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert symbol data with candles array to normalized records
        Returns list of OHLCV records
        """
        normalized_records = []
        
        try:
            symbol = symbol_data.get('symbol', '')
            candles = symbol_data.get('candles', [])
            resolution = symbol_data.get('resolution', '5')
            fetch_timestamp = symbol_data.get('timestamp', '')
            
            # Clean symbol name (remove NSE: and -EQ)
            symbol_clean = symbol.replace('NSE:', '').replace('-EQ', '')
            
            for candle in candles:
                if len(candle) >= 6:  # [timestamp, open, high, low, close, volume]
                    timestamp_unix = candle[0]
                    open_price = candle[1]
                    high_price = candle[2]
                    low_price = candle[3]
                    close_price = candle[4]
                    volume = candle[5]
                    
                    # Convert Unix timestamp to ISO datetime
                    try:
                        dt = datetime.fromtimestamp(timestamp_unix)
                        timestamp_iso = dt.isoformat()
                        
                        record = {
                            'symbol': symbol,
                            'symbol_clean': symbol_clean,
                            'timestamp_unix': timestamp_unix,
                            'timestamp_iso': timestamp_iso,
                            'open': float(open_price) if open_price is not None else 0.0,
                            'high': float(high_price) if high_price is not None else 0.0,
                            'low': float(low_price) if low_price is not None else 0.0,
                            'close': float(close_price) if close_price is not None else 0.0,
                            'volume': int(volume) if volume is not None else 0,
                            'resolution': resolution,
                            'fetch_timestamp': fetch_timestamp,
                            'year': dt.year,
                            'month': dt.month,
                            'day': dt.day,
                            'hour': dt.hour,
                            'processed_at': datetime.utcnow().isoformat()
                        }
                        
                        # Data quality checks
                        if (record['high'] >= record['low'] and 
                            record['volume'] >= 0 and 
                            record['close'] > 0):
                            normalized_records.append(record)
                            
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error processing candle for {symbol}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error normalizing symbol data: {e}")
            
        return normalized_records
    
    def process_raw_json(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process raw JSON data and extract all OHLCV records
        """
        all_records = []
        
        try:
            # Extract data section
            data_section = raw_data.get('data', {})
            
            for symbol_key, symbol_data in data_section.items():
                records = self.normalize_ohlcv_record(symbol_data)
                all_records.extend(records)
                
            logger.info(f"Processed {len(all_records)} OHLCV records from {len(data_section)} symbols")
            
        except Exception as e:
            logger.error(f"Error processing raw JSON: {e}")
            
        return all_records
    
    def records_to_csv(self, records: List[Dict[str, Any]]) -> str:
        """
        Convert records to CSV format using StringIO
        Returns CSV string
        """
        if not records:
            return ""
            
        output = StringIO()
        
        # Define CSV headers
        headers = [
            'symbol', 'symbol_clean', 'timestamp_unix', 'timestamp_iso',
            'open', 'high', 'low', 'close', 'volume', 'resolution',
            'fetch_timestamp', 'year', 'month', 'day', 'hour', 'processed_at'
        ]
        
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        
        for record in records:
            writer.writerow(record)
            
        csv_content = output.getvalue()
        output.close()
        
        return csv_content
    
    def upload_csv_to_s3(self, bucket: str, csv_content: str, s3_key: str, compress: bool = True) -> bool:
        """
        Upload CSV content to S3, optionally compressed
        """
        try:
            if compress:
                # Compress with gzip
                csv_bytes = csv_content.encode('utf-8')
                compressed_content = gzip.compress(csv_bytes)
                content_encoding = 'gzip'
                content_type = 'text/csv'
                s3_key += '.gz'
                body = compressed_content
            else:
                body = csv_content.encode('utf-8')
                content_encoding = None
                content_type = 'text/csv'
            
            # Upload to S3
            put_kwargs = {
                'Bucket': bucket,
                'Key': s3_key,
                'Body': body,
                'ContentType': content_type,
                'Metadata': {
                    'processed_at': datetime.utcnow().isoformat(),
                    'format': 'csv',
                    'source': 'lightweight_etl'
                }
            }
            
            if content_encoding:
                put_kwargs['ContentEncoding'] = content_encoding
            
            self.s3_client.put_object(**put_kwargs)
            
            logger.info(f"Successfully uploaded CSV to s3://{bucket}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload CSV to S3: {e}")
            return False
    
    def list_raw_files(self, bucket: str, date_prefix: str) -> List[str]:
        """
        List raw JSON files for a specific date
        """
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            keys = []
            
            for page in paginator.paginate(Bucket=bucket, Prefix=date_prefix):
                for obj in page.get('Contents', []):
                    if obj['Key'].endswith('.json'):
                        keys.append(obj['Key'])
                        
            logger.info(f"Found {len(keys)} raw JSON files for prefix: {date_prefix}")
            return keys
            
        except Exception as e:
            logger.error(f"Error listing raw files: {e}")
            return []
    
    def download_json_file(self, bucket: str, key: str) -> Optional[Dict[str, Any]]:
        """
        Download and parse JSON file from S3
        """
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            json_content = response['Body'].read().decode('utf-8')
            return json.loads(json_content)
            
        except Exception as e:
            logger.error(f"Error downloading {key}: {e}")
            return None
    
    def process_date(self, bucket: str, processing_date: datetime) -> Dict[str, Any]:
        """
        Process all raw files for a specific date
        """
        try:
            # Create date prefix for raw files
            date_str = processing_date.strftime('%Y-%m-%d')
            raw_prefix = f"Raw data/Prices/{date_str}/"
            
            # List raw files
            raw_keys = self.list_raw_files(bucket, raw_prefix)
            
            if not raw_keys:
                logger.warning(f"No raw files found for date: {date_str}")
                return {
                    'processed_files': 0,
                    'total_records': 0,
                    'symbols_processed': 0,
                    'date': date_str
                }
            
            # Process ONLY the latest raw file (each file contains full day's data)
            # Sort keys by timestamp descending and take the first one
            raw_keys_sorted = sorted(raw_keys, reverse=True)
            latest_key = raw_keys_sorted[0]
            
            logger.info(f"Processing latest raw file: {latest_key} (ignoring {len(raw_keys)-1} older duplicate files)")
            
            all_records = []
            processed_files = 0
            symbols_set = set()
            
            raw_data = self.download_json_file(bucket, latest_key)
            if raw_data:
                records = self.process_raw_json(raw_data)
                all_records.extend(records)
                processed_files = 1
                
                # Track unique symbols
                for record in records:
                    symbols_set.add(record['symbol_clean'])
            
            # Group records by symbol for partitioned output
            records_by_symbol = {}
            for record in all_records:
                symbol = record['symbol_clean']
                if symbol not in records_by_symbol:
                    records_by_symbol[symbol] = []
                records_by_symbol[symbol].append(record)
            
            # Write CSV files per symbol (partitioned approach)
            uploaded_files = 0
            total_records = len(all_records)
            
            for symbol, symbol_records in records_by_symbol.items():
                csv_content = self.records_to_csv(symbol_records)
                
                if csv_content:
                    # Create partitioned S3 key
                    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                    csv_key = f"analytics/csv/symbol={symbol}/year={processing_date.year}/month={processing_date.month:02d}/day={processing_date.day:02d}/data_{timestamp}.csv"
                    
                    if self.upload_csv_to_s3(bucket, csv_content, csv_key, compress=True):
                        uploaded_files += 1
            
            logger.info(f"Processed {processed_files} files, {total_records} records, {len(symbols_set)} symbols")
            
            return {
                'processed_files': processed_files,
                'total_records': total_records,
                'symbols_processed': len(symbols_set),
                'uploaded_files': uploaded_files,
                'date': date_str,
                'symbols': sorted(list(symbols_set))
            }
            
        except Exception as e:
            logger.error(f"Error processing date {processing_date}: {e}")
            raise

def lambda_handler(event, context):
    """
    AWS Lambda handler for lightweight ETL processing
    """
    try:
        logger.info("Starting lightweight ETL processing")
        
        # Get configuration
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
        
        if not bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable is required")
        
        # Determine processing date
        if 'date' in event:
            processing_date = datetime.strptime(event['date'], '%Y-%m-%d')
        else:
            # Default to today (ETL runs at 4 PM after market close, processes same day's data)
            processing_date = datetime.utcnow()
        
        # Initialize ETL processor
        etl = LightweightETL()
        
        # Process the date
        result = etl.process_date(bucket_name, processing_date)
        
        # Send notification if SNS topic provided
        if sns_topic_arn and result['total_records'] > 0:
            message = f"""
Lightweight ETL Processing Completed Successfully

Date: {result['date']}
Files Processed: {result['processed_files']}
Records Processed: {result['total_records']}
Symbols: {result['symbols_processed']}
CSV Files Created: {result['uploaded_files']}
Symbols List: {', '.join(result['symbols'][:10])}{'...' if len(result['symbols']) > 10 else ''}

Output Location: s3://{bucket_name}/analytics/csv/
            """
            
            etl.sns_client.publish(
                TopicArn=sns_topic_arn,
                Subject="Lightweight ETL Success",
                Message=message.strip()
            )
        
        logger.info(f"ETL processing completed: {result}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"ETL processing failed: {error_msg}")
        
        # Send failure notification
        sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
        if sns_topic_arn:
            try:
                sns_client = boto3.client('sns')
                sns_client.publish(
                    TopicArn=sns_topic_arn,
                    Subject="Lightweight ETL FAILURE",
                    Message=f"ETL processing failed at {datetime.utcnow().isoformat()}\nError: {error_msg}"
                )
            except Exception as sns_error:
                logger.error(f"Failed to send SNS notification: {sns_error}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }

if __name__ == "__main__":
    # CLI support for local testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Run lightweight ETL processing")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--date", help="Date to process (YYYY-MM-DD), defaults to yesterday")
    
    args = parser.parse_args()
    
    # Set environment for CLI execution
    os.environ['S3_BUCKET_NAME'] = args.bucket
    
    if args.date:
        event = {'date': args.date}
    else:
        event = {}
    
    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))