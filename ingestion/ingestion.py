#!/usr/bin/env python3
"""
Stock Price Ingestion Module for Fyers API
Fetches OHLCV data and stores in S3 raw zone
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import boto3
import requests
from botocore.exceptions import ClientError
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/ingestion.log')
    ]
)
logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit breaker pattern for API calls"""
    
    def __init__(self, failure_threshold=5, timeout=60, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")
                
        try:
            result = func(*args, **kwargs)
            self.reset()
            return result
        except self.expected_exception as e:
            self.record_failure()
            raise e
            
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
    def reset(self):
        self.failure_count = 0
        self.state = 'CLOSED'

class FyersAPIClient:
    """Fyers API client for stock data ingestion with circuit breaker"""
    
    def __init__(self):
        self.base_url = "https://api-t1.fyers.in/data-rest/v3"
        self.access_token = None
        self.client_id = None
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout=300,  # 5 minutes
            expected_exception=requests.exceptions.RequestException
        )
        self.rate_limit_delay = 0.5  # 500ms between requests
        
    def get_credentials_from_secrets(self) -> Dict[str, str]:
        """Retrieve Fyers API credentials from AWS Secrets Manager"""
        try:
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            )
            
            secret_name = os.getenv('FYERS_SECRET_NAME', 'fyers-api-credentials')
            response = client.get_secret_value(SecretId=secret_name)
            secret = json.loads(response['SecretString'])
            
            required_keys = ['access_token', 'client_id', 'refresh_token']
            for key in required_keys:
                if key not in secret:
                    raise ValueError(f"Missing required credential: {key}")
            
            self.access_token = secret['access_token']
            self.client_id = secret['client_id']
            
            logger.info("Successfully retrieved Fyers API credentials")
            return secret
            
        except ClientError as e:
            logger.error(f"Failed to retrieve secrets: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse secrets JSON: {e}")
            raise
            
    def refresh_access_token(self, refresh_token: str) -> bool:
        """Refresh the access token using refresh token"""
        try:
            url = f"{self.base_url}/auth/refresh-token"
            headers = {
                'Content-Type': 'application/json'
            }
            payload = {
                'refresh_token': refresh_token,
                'client_id': self.client_id
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 200:
                self.access_token = data['data']['access_token']
                logger.info("Successfully refreshed access token")
                return True
            else:
                logger.error(f"Token refresh failed: {data.get('message', 'Unknown error')}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to refresh token: {e}")
            return False
            
    def get_top_nse_symbols(self) -> List[str]:
        """Get top NSE stock symbols - simplified list for MVP"""
        # In production, this could be fetched from a dynamic source
        top_symbols = [
            'NSE:RELIANCE-EQ', 'NSE:TCS-EQ', 'NSE:HDFCBANK-EQ', 'NSE:INFY-EQ',
            'NSE:HINDUNILVR-EQ', 'NSE:ICICIBANK-EQ', 'NSE:KOTAKBANK-EQ', 
            'NSE:SBIN-EQ', 'NSE:BHARTIARTL-EQ', 'NSE:ITC-EQ', 'NSE:ASIANPAINT-EQ',
            'NSE:LT-EQ', 'NSE:AXISBANK-EQ', 'NSE:MARUTI-EQ', 'NSE:SUNPHARMA-EQ',
            'NSE:TITAN-EQ', 'NSE:ULTRACEMCO-EQ', 'NSE:NESTLEIND-EQ', 'NSE:WIPRO-EQ',
            'NSE:M&M-EQ', 'NSE:TECHM-EQ', 'NSE:NTPC-EQ', 'NSE:HCLTECH-EQ',
            'NSE:POWERGRID-EQ', 'NSE:TATASTEEL-EQ', 'NSE:JSWSTEEL-EQ',
            'NSE:ADANIPORTS-EQ', 'NSE:COALINDIA-EQ', 'NSE:ONGC-EQ', 'NSE:IOC-EQ'
        ]
        return top_symbols
        
    def get_ohlcv_data(self, symbols: List[str], resolution: str = "5") -> Optional[Dict]:
        """
        Fetch OHLCV data for given symbols with circuit breaker and advanced retry
        """
        try:
            if not self.access_token:
                raise ValueError("Access token not available")
                
            # Calculate time range (last 5 minutes)
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=10)  # Buffer for data availability
            
            url = f"{self.base_url}/history"
            headers = {
                'Authorization': f"{self.client_id}:{self.access_token}",
                'Content-Type': 'application/json'
            }
            
            all_data = {}
            failed_symbols = []
            successful_requests = 0
            total_requests = len(symbols)
            
            # Process symbols in batches to avoid overwhelming the API
            batch_size = 5
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                
                for symbol in batch:
                    try:
                        # Use circuit breaker for API calls
                        result = self.circuit_breaker.call(
                            self._fetch_symbol_data,
                            symbol, url, headers, start_time, end_time, resolution
                        )
                        
                        if result:
                            all_data[symbol] = result
                            successful_requests += 1
                            logger.info(f"✅ Fetched data for {symbol}: {len(result['candles'])} records")
                        else:
                            failed_symbols.append(symbol)
                            logger.warning(f"❌ No data for {symbol}")
                            
                    except Exception as e:
                        logger.error(f"❌ Failed to fetch {symbol}: {e}")
                        failed_symbols.append(symbol)
                        
                    # Rate limiting
                    time.sleep(self.rate_limit_delay)
                    
                # Batch delay
                if i + batch_size < len(symbols):
                    time.sleep(2)  # 2 second delay between batches
                    
            # Calculate success rate
            success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0
            logger.info(f"📊 Success rate: {success_rate:.1f}% ({successful_requests}/{total_requests})")
            
            return {
                'data': all_data,
                'metadata': {
                    'total_symbols_requested': total_requests,
                    'successful_symbols': successful_requests,
                    'failed_symbols': failed_symbols,
                    'success_rate_percent': round(success_rate, 2),
                    'ingestion_timestamp': datetime.utcnow().isoformat(),
                    'resolution': resolution,
                    'circuit_breaker_state': self.circuit_breaker.state
                }
            }
            
        except Exception as e:
            logger.error(f"💥 Critical failure in OHLCV data fetching: {e}")
            return None
            
    def _fetch_symbol_data(self, symbol: str, url: str, headers: dict, 
                          start_time: datetime, end_time: datetime, resolution: str) -> Optional[Dict]:
        """Internal method to fetch data for a single symbol with retries"""
        retry_count = 3
        
        for attempt in range(retry_count):
            try:
                params = {
                    'symbol': symbol,
                    'resolution': resolution,
                    'date_format': '1',  # Unix timestamp
                    'range_from': int(start_time.timestamp()),
                    'range_to': int(end_time.timestamp()),
                    'cont_flag': '1'
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                if data.get('code') == 200 and data.get('candles'):
                    return {
                        'symbol': symbol,
                        'resolution': resolution,
                        'candles': data['candles'],
                        'timestamp': datetime.utcnow().isoformat(),
                        'metadata': {
                            'total_records': len(data['candles']),
                            'fetch_time': datetime.utcnow().isoformat(),
                            'attempt_number': attempt + 1,
                            'time_range': {
                                'from': start_time.isoformat(),
                                'to': end_time.isoformat()
                            }
                        }
                    }
                else:
                    if attempt == retry_count - 1:  # Last attempt
                        logger.warning(f"No data available for {symbol}: {data.get('message', 'Unknown error')}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                if attempt == retry_count - 1:  # Last attempt
                    raise e
                else:
                    wait_time = (2 ** attempt) + (time.time() % 1)  # Jittered exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed for {symbol}, retrying in {wait_time:.1f}s: {e}")
                    time.sleep(wait_time)
                    
        return None

class S3DataUploader:
    """Handles S3 data uploads with proper partitioning"""
    
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
        
    def upload_raw_data(self, data: Dict, timestamp: datetime = None) -> bool:
        """Upload raw JSON data to S3 with date partitioning"""
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
                
            # Create S3 key with partitioning
            year = timestamp.strftime('%Y')
            month = timestamp.strftime('%m')
            day = timestamp.strftime('%d')
            hour = timestamp.strftime('%H')
            minute = timestamp.strftime('%M')
            
            key = f"raw/yyyy={year}/mm={month}/dd={day}/ohlcv_data_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            
            # Convert data to JSON string
            json_data = json.dumps(data, indent=2)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json_data.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'ingestion_timestamp': timestamp.isoformat(),
                    'data_type': 'ohlcv_raw',
                    'source': 'fyers_api'
                }
            )
            
            logger.info(f"Successfully uploaded data to s3://{self.bucket_name}/{key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload data to S3: {e}")
            return False

def send_sns_notification(topic_arn: str, subject: str, message: str) -> bool:
    """Send SNS notification for monitoring"""
    try:
        sns_client = boto3.client('sns')
        response = sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
        logger.info(f"SNS notification sent: {response.get('MessageId')}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SNS notification: {e}")
        return False

def main():
    """Main ingestion workflow"""
    try:
        logger.info("Starting stock data ingestion process")
        
        # Get configuration from environment
        bucket_name = os.getenv('S3_BUCKET_NAME', 'your-org-pbl-ohlcv')
        sns_topic_arn = os.getenv('SNS_TOPIC_ARN')
        
        # Initialize Fyers API client
        fyers_client = FyersAPIClient()
        credentials = fyers_client.get_credentials_from_secrets()
        
        # Try to refresh token if needed
        if not fyers_client.access_token:
            refresh_success = fyers_client.refresh_access_token(credentials['refresh_token'])
            if not refresh_success:
                raise Exception("Failed to refresh access token")
        
        # Get stock symbols
        symbols = fyers_client.get_top_nse_symbols()
        logger.info(f"Fetching data for {len(symbols)} symbols")
        
        # Fetch OHLCV data
        ohlcv_data = fyers_client.get_ohlcv_data(symbols)
        if not ohlcv_data:
            raise Exception("Failed to fetch OHLCV data")
        
        # Upload to S3
        s3_uploader = S3DataUploader(bucket_name)
        upload_success = s3_uploader.upload_raw_data(ohlcv_data)
        
        if not upload_success:
            raise Exception("Failed to upload data to S3")
        
        # Log success metrics
        successful_symbols = ohlcv_data['metadata']['successful_symbols']
        failed_symbols = len(ohlcv_data['metadata']['failed_symbols'])
        
        logger.info(f"Ingestion completed successfully: {successful_symbols} successful, {failed_symbols} failed")
        
        # Send success notification
        if sns_topic_arn:
            message = f"""
Stock data ingestion completed successfully.

Statistics:
- Successful symbols: {successful_symbols}
- Failed symbols: {failed_symbols}
- Ingestion time: {datetime.utcnow().isoformat()}
- S3 bucket: {bucket_name}
            """
            send_sns_notification(
                sns_topic_arn,
                "Stock Data Ingestion - Success",
                message.strip()
            )
        
        return 0
        
    except Exception as e:
        error_msg = f"Stock data ingestion failed: {str(e)}"
        logger.error(error_msg)
        
        # Send failure notification
        sns_topic_arn = os.getenv('SNS_TOPIC_ARN')
        if sns_topic_arn:
            send_sns_notification(
                sns_topic_arn,
                "Stock Data Ingestion - FAILURE",
                f"Ingestion failed at {datetime.utcnow().isoformat()}\nError: {error_msg}"
            )
        
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)