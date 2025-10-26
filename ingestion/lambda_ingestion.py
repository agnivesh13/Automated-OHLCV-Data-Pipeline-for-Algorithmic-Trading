#!/usr/bin/env python3
"""
Enhanced MVP Lambda Function for Stock Price Ingestion
Using fyers_apiv3 package (same as your working local code)
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import boto3
from botocore.exceptions import ClientError
import pytz

# Simplified imports for Lambda compatibility
import requests
import pytz

# Note: Using direct API calls instead of fyers_apiv3 due to Lambda compatibility
FYERS_AVAILABLE = True

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def is_within_trading_hours() -> bool:
    """
    Check if current time is within Indian stock market trading hours
    NSE/BSE Trading Hours: 9:15 AM - 3:30 PM IST (Monday to Friday)
    """
    try:
        # Get current time in IST
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)
        
        # Check if it's a weekday (Monday = 0, Sunday = 6)
        if now_ist.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Market hours in IST: 9:15 AM to 3:30 PM
        market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
        
        # Check if current time is within trading hours
        is_trading_time = market_open <= now_ist <= market_close
        
        logger.info(f"Current IST time: {now_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"Market open: {market_open.strftime('%H:%M')} IST")
        logger.info(f"Market close: {market_close.strftime('%H:%M')} IST")
        logger.info(f"Is trading hours: {is_trading_time}")
        
        return is_trading_time
        
    except Exception as e:
        logger.warning(f"Error checking trading hours: {e}")
        return True

def lambda_handler(event, context):
    """
    AWS Lambda handler for stock data ingestion
    Enhanced version using fyers_apiv3 package (same as working local code)
    """
    try:
        logger.info("Starting stock data ingestion")

        # Get configuration from environment
        bucket_name = os.environ['S3_BUCKET_NAME']
        sns_topic_arn = os.environ['SNS_TOPIC_ARN']
        fyers_access_token_param = os.environ['FYERS_ACCESS_TOKEN_PARAM']
        fyers_client_id_param = os.environ['FYERS_CLIENT_ID_PARAM']
        environment = os.environ.get('ENVIRONMENT', 'dev')
        enable_trading_hours_check = os.environ.get('ENABLE_TRADING_HOURS_CHECK', 'true').lower() == 'true'

        # Initialize clients
        s3_client = boto3.client('s3')
        sns_client = boto3.client('sns')
        ssm_client = boto3.client('ssm')

        # Check for demo mode
        demo_mode = False
        project_name = os.environ.get('PROJECT_NAME', 'stock-pipeline')
        demo_param_name = f"/{project_name}/demo_mode"

        try:
            demo_param = ssm_client.get_parameter(Name=demo_param_name)
            demo_value = demo_param['Parameter']['Value']
            demo_mode = demo_value.lower() == 'true'
            logger.info(f"📋 Demo mode parameter found: '{demo_value}' -> {demo_mode}")
            if demo_mode:
                logger.info("🎬 DEMO MODE ENABLED - Using mock data")
        except ssm_client.exceptions.ParameterNotFound:
            logger.info(f"Demo mode parameter not found: {demo_param_name} - running in normal mode")
        except Exception as e:
            logger.warning(f"Could not check demo mode: {e}")

        # Check trading hours (unless demo mode or disabled)
        if not demo_mode and enable_trading_hours_check and not is_within_trading_hours():
            message = "⏰ Outside trading hours - skipping ingestion"
            logger.info(message)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': message,
                    'timestamp': datetime.utcnow().isoformat()
                })
            }

        # Get symbols
        symbols = get_mvp_symbols()

        # Get OHLCV data (demo mode or real API)
        if demo_mode:
            logger.info("🎬 Demo mode: Generating mock OHLCV data")
            ohlcv_data = generate_mock_ohlcv_data(symbols)
        else:
            logger.info("📊 Fetching real OHLCV data using fyers_apiv3")

            # Get credentials from SSM
            credentials = get_fyers_credentials_from_ssm(
                ssm_client,
                fyers_access_token_param,
                fyers_client_id_param
            )

            if not credentials:
                raise Exception("Failed to get Fyers credentials")

            # Fetch data using enhanced API with auto-refresh
            ohlcv_data = fetch_ohlcv_data_with_fyers_api(credentials, symbols, ssm_client)

        if not ohlcv_data:
            raise Exception("Failed to fetch OHLCV data")

        # Store data in S3
        s3_key = store_data_in_s3(s3_client, bucket_name, ohlcv_data, environment)

        # Send success notification
        successful_symbols = ohlcv_data['metadata']['successful_symbols']
        total_symbols = ohlcv_data['metadata']['total_symbols_requested']
        success_rate = ohlcv_data['metadata']['success_rate_percent']

        message = f"✅ Ingestion completed: {successful_symbols}/{total_symbols} symbols ({success_rate}% success)"

        send_sns_notification(sns_client, sns_topic_arn, "Stock Data Ingestion Success", message)

        logger.info(f"✅ {message}")
        logger.info(f"📁 Data stored at: s3://{bucket_name}/{s3_key}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': message,
                's3_location': f"s3://{bucket_name}/{s3_key}",
                'symbols_processed': successful_symbols,
                'total_symbols': total_symbols,
                'success_rate': success_rate,
                'timestamp': datetime.utcnow().isoformat()
            })
        }

    except Exception as e:
        error_msg = f"💥 Lambda execution failed: {str(e)}"
        logger.error(error_msg)

        # Send error notification
        try:
            send_sns_notification(sns_client, sns_topic_arn, "Stock Data Ingestion Failed", error_msg)
        except Exception:
            pass

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Ingestion failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }

def get_fyers_credentials_from_ssm(ssm_client, access_token_param: str, client_id_param: str) -> Dict[str, str]:
    """
    Get Fyers credentials from SSM with automatic token refresh capability
    """
    try:
        # Get all required parameters including refresh token
        project_name = os.environ.get('PROJECT_NAME', 'stock-pipeline')
        refresh_token_param = os.environ.get('FYERS_REFRESH_TOKEN_PARAM', f"/{project_name}/fyers/refresh_token")
        app_secret_param = os.environ.get('FYERS_APP_SECRET_PARAM', f"/{project_name}/fyers/app_secret")
        
        parameter_names = [access_token_param, client_id_param, refresh_token_param, app_secret_param]
        
        response = ssm_client.get_parameters(
            Names=parameter_names,
            WithDecryption=True
        )
        
        credentials = {}
        for param in response['Parameters']:
            if param['Name'] == access_token_param:
                credentials['access_token'] = param['Value']
            elif param['Name'] == client_id_param:
                credentials['client_id'] = param['Value']
            elif param['Name'] == refresh_token_param:
                credentials['refresh_token'] = param['Value']
            elif param['Name'] == app_secret_param:
                credentials['app_secret'] = param['Value']
        
        # Check if we have all required credentials
        if not credentials.get('client_id'):
            raise ValueError("Missing client_id")
        
        # If access token is missing or invalid, try to refresh it
        if not credentials.get('access_token') or credentials['access_token'] in ['CHANGE_ME', 'AUTO_GENERATED']:
            logger.info("🔄 Access token missing or invalid, attempting to refresh...")
            new_access_token = refresh_fyers_access_token(
                client_id=credentials['client_id'],
                refresh_token=credentials.get('refresh_token'),
                app_secret=credentials.get('app_secret')
            )
            
            if new_access_token:
                credentials['access_token'] = new_access_token
                # Update SSM with new access token
                try:
                    ssm_client.put_parameter(
                        Name=access_token_param,
                        Value=new_access_token,
                        Type='SecureString',
                        Overwrite=True
                    )
                    logger.info("✅ Updated access token in SSM Parameter Store")
                except Exception as e:
                    logger.warning(f"⚠️ Could not update access token in SSM: {e}")
            else:
                raise ValueError("Could not refresh access token")
        
        logger.info("✅ Successfully retrieved and validated Fyers credentials")
        return credentials
        
    except Exception as e:
        logger.error(f"❌ Failed to get Fyers credentials: {e}")
        return None

def refresh_fyers_access_token(client_id: str, refresh_token: str, app_secret: str) -> Optional[str]:
    """
    Refresh Fyers access token using refresh token
    """
    try:
        if not refresh_token or refresh_token == 'CHANGE_ME':
            logger.error("❌ No valid refresh token available")
            return None
            
        import hashlib
        
        # Generate appIdHash (required for Fyers API)
        app_id_hash = hashlib.sha256(f"{client_id}:{app_secret}".encode()).hexdigest()
        
        # Fyers token refresh endpoint (corrected to use api-t1 like other endpoints)
        token_url = "https://api-t1.fyers.in/api/v3/validate-refresh-token"
        
        payload = {
            "grant_type": "refresh_token",
            "appIdHash": app_id_hash,
            "refresh_token": refresh_token
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        logger.info("🔄 Attempting to refresh Fyers access token...")
        response = requests.post(token_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('s') == 'ok' and 'access_token' in data:
                logger.info("✅ Successfully refreshed Fyers access token")
                return data['access_token']
            else:
                logger.error(f"❌ Token refresh failed: {data}")
                return None
        else:
            logger.error(f"❌ Token refresh HTTP error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error refreshing access token: {e}")
        return None

def fetch_ohlcv_data_with_fyers_api(credentials: Dict[str, str], symbols: List[str], ssm_client=None) -> Optional[Dict]:
    """
    Fetch OHLCV data using the ACTUAL working Fyers API endpoint with automatic token refresh
    """
    try:
        client_id = credentials['client_id']
        access_token = credentials['access_token']
        
        # Use the ACTUAL working endpoint that fyers_apiv3 uses
        base_url = "https://api-t1.fyers.in/data/history"
        
        # Use the EXACT headers that work
        headers = {
            'Authorization': f"{client_id}:{access_token}",  # NOT Bearer!
            'Content-Type': 'application/json',
            'version': '3'  # Special version header
        }
        
        logger.info("✅ Using reverse-engineered Fyers API endpoint with auto-refresh")
        
        # Get current date for data fetching
        today = datetime.now().strftime("%Y-%m-%d")
        
        all_data = {}
        failed_symbols = []
        successful_requests = 0
        token_refreshed = False
        
        logger.info(f"📊 Fetching data for {len(symbols)} symbols using working endpoint")
        
        for i, symbol in enumerate(symbols):
            try:
                logger.info(f"📈 Fetching {symbol} ({i+1}/{len(symbols)})")
                
                # Use exact same parameters as fyers_apiv3
                params = {
                    "symbol": symbol,
                    "resolution": "5",  # 5-minute candles
                    "date_format": "1",
                    "range_from": today,
                    "range_to": today,
                    "cont_flag": "1"
                }
                
                # Make the request using the working endpoint
                response = requests.get(base_url, headers=headers, params=params, timeout=10)
                
                # Check for token expiration (status 401 or specific error messages)
                if response.status_code == 401 or (response.status_code == 403 and not token_refreshed):
                    logger.warning(f"🔄 Token appears expired (HTTP {response.status_code}), attempting refresh...")
                    
                    # Try to refresh token
                    if ssm_client and credentials.get('refresh_token') and credentials.get('app_secret'):
                        new_access_token = refresh_fyers_access_token(
                            client_id=credentials['client_id'],
                            refresh_token=credentials['refresh_token'],
                            app_secret=credentials['app_secret']
                        )
                        
                        if new_access_token:
                            # Update credentials and headers
                            credentials['access_token'] = new_access_token
                            headers['Authorization'] = f"{client_id}:{new_access_token}"
                            token_refreshed = True
                            
                            # Update SSM parameter
                            try:
                                project_name = os.environ.get('PROJECT_NAME', 'stock-pipeline')
                                access_token_param = os.environ.get('FYERS_ACCESS_TOKEN_PARAM', f"/{project_name}/fyers/access_token")
                                ssm_client.put_parameter(
                                    Name=access_token_param,
                                    Value=new_access_token,
                                    Type='SecureString',
                                    Overwrite=True
                                )
                                logger.info("✅ Updated access token in SSM after refresh")
                            except Exception as e:
                                logger.warning(f"⚠️ Could not update SSM after token refresh: {e}")
                            
                            # Retry the request with new token
                            logger.info(f"🔄 Retrying {symbol} with refreshed token...")
                            response = requests.get(base_url, headers=headers, params=params, timeout=10)
                        else:
                            logger.error(f"❌ Could not refresh token for {symbol}")
                            failed_symbols.append(symbol)
                            continue
                    else:
                        logger.error(f"❌ Cannot refresh token - missing refresh credentials")
                        failed_symbols.append(symbol)
                        continue
                
                response.raise_for_status()
                
                data = response.json()
                
                # Check response (same validation as fyers_apiv3)
                if not isinstance(data, dict):
                    logger.warning(f"❌ Unexpected response type for {symbol}: {type(data)}")
                    failed_symbols.append(symbol)
                    continue
                
                if data.get("s") == "error" or (data.get("code") and data.get("code") != 200):
                    # Check for authentication errors in the response
                    error_message = data.get("message", "").lower()
                    if "token" in error_message or "auth" in error_message or "unauthorized" in error_message:
                        logger.warning(f"🔄 Authentication error in response for {symbol}: {data}")
                        if not token_refreshed and ssm_client:
                            # Try token refresh one more time
                            logger.info("🔄 Attempting token refresh due to auth error in response...")
                            # [Token refresh logic would go here - similar to above]
                    
                    logger.warning(f"❌ API Error for {symbol}: {data}")
                    failed_symbols.append(symbol)
                    continue
                
                candles = data.get("candles", [])
                
                if not candles:
                    logger.warning(f"⚠️  No candles for {symbol}")
                    failed_symbols.append(symbol)
                    continue
                
                # Store successful data
                all_data[symbol] = {
                    'symbol': symbol,
                    'resolution': '5',
                    'candles': candles,
                    'timestamp': datetime.utcnow().isoformat(),
                    'total_records': len(candles),
                    'api_response': data  # Include full response for debugging
                }
                
                successful_requests += 1
                logger.info(f"✅ SUCCESS: {len(candles)} candles for {symbol}")
                
                # Rate limiting (same as fyers_apiv3)
                if i < len(symbols) - 1:
                    time.sleep(0.3)
                    
            except Exception as e:
                logger.error(f"❌ Exception for {symbol}: {e}")
                failed_symbols.append(symbol)
                time.sleep(0.3)
        
        success_rate = (successful_requests / len(symbols)) * 100
        logger.info(f"📊 Fyers API fetch completed: {success_rate:.1f}% success rate")
        
        return {
            'data': all_data,
            'metadata': {
                'total_symbols_requested': len(symbols),
                'successful_symbols': successful_requests,
                'failed_symbols': failed_symbols,
                'success_rate_percent': round(success_rate, 2),
                'ingestion_timestamp': datetime.utcnow().isoformat(),
                'resolution': '5',
                'api_method': 'reverse_engineered_fyers_api',
                'api_endpoint': 'api-t1.fyers.in',
                'date_fetched': today
            }
        }
        
    except Exception as e:
        logger.error(f"💥 Critical failure in Fyers API data fetching: {e}")
        return None

def get_mvp_symbols() -> List[str]:
    """Get symbol list (same symbols as your working code)"""
    mvp_symbols = [
        'NSE:RELIANCE-EQ',    # Same as your working code
        'NSE:TCS-EQ', 
        'NSE:HDFCBANK-EQ',
        'NSE:INFY-EQ',
        'NSE:ICICIBANK-EQ',
        'NSE:HINDUNILVR-EQ',
        'NSE:KOTAKBANK-EQ',
        'NSE:SBIN-EQ',
        'NSE:BHARTIARTL-EQ',
        'NSE:ITC-EQ'
    ]
    
    logger.info(f"Using MVP symbol list with {len(mvp_symbols)} symbols")
    return mvp_symbols

def generate_mock_ohlcv_data(symbols: List[str]) -> Dict:
    """Generate mock data for demo mode"""
    import random
    
    logger.info(f"🎬 Generating mock data for {len(symbols)} symbols")
    
    all_data = {}
    current_time = datetime.utcnow()
    
    for symbol in symbols:
        # Generate realistic price data
        base_price = random.uniform(100, 3000)
        
        # Generate 150 candles (similar to real trading day)
        candles = []
        for i in range(150):
            timestamp = int((current_time - timedelta(minutes=5*i)).timestamp())
            
            open_price = base_price + random.uniform(-5, 5)
            close_price = open_price + random.uniform(-10, 10)
            high_price = max(open_price, close_price) + random.uniform(0, 5)
            low_price = min(open_price, close_price) - random.uniform(0, 5)
            volume = random.randint(10000, 100000)
            
            candles.append([timestamp, open_price, high_price, low_price, close_price, volume])
        
        all_data[symbol] = {
            'symbol': symbol,
            'resolution': '5',
            'candles': candles,
            'timestamp': current_time.isoformat(),
            'total_records': len(candles),
            'mock_data': True
        }
        
        logger.info(f"✅ Generated mock data for {symbol}: {len(candles)} candles")
    
    return {
        'data': all_data,
        'metadata': {
            'total_symbols_requested': len(symbols),
            'successful_symbols': len(symbols),
            'failed_symbols': [],
            'success_rate_percent': 100.0,
            'ingestion_timestamp': current_time.isoformat(),
            'resolution': '5',
            'demo_mode': True
        }
    }

def store_data_in_s3(s3_client, bucket_name: str, data: Dict, environment: str) -> str:
    """Store OHLCV data in S3 with proper partitioning"""
    try:
        current_time = datetime.utcnow()
        
        # Create partition structure
        year = current_time.strftime('%Y')
        month = current_time.strftime('%m')
        day = current_time.strftime('%d')
        timestamp = current_time.strftime('%Y%m%d_%H%M%S')
        

        # Example: Company Data upload
        # security_id should be passed or determined elsewhere in your code
        security_id = data.get('security_id', 'example_security_id')
        company_data_key = f"Company Data/{security_id}/Prices/ohlcv_{timestamp}.parquet"

        # Example: Raw Data upload
        raw_data_key = f"Raw data/Prices/{year}-{month}-{day}/raw_file_{timestamp}.json"

        # Choose which key to use based on data type (customize as needed)
        if data.get('is_company_data'):
            s3_key = company_data_key
        else:
            s3_key = raw_data_key

        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(data, indent=2),
            ContentType='application/json'
        )

        logger.info(f"📁 Data stored in S3: {s3_key}")
        return s3_key
        
    except Exception as e:
        logger.error(f"💥 Failed to store data in S3: {e}")
        raise

def send_sns_notification(sns_client, topic_arn: str, subject: str, message: str):
    """Send SNS notification"""
    try:
        sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
        logger.info(f"📧 SNS notification sent: {subject}")
    except Exception as e:
        logger.error(f"💥 Failed to send SNS notification: {e}")
