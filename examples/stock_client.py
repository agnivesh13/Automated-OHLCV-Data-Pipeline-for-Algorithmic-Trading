"""
Stock Data Client Library
Simple Python client for accessing stock price data from the pipeline
"""

import boto3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import pandas as pd

class StockDataClient:
    """Client for accessing stock price data from S3"""
    
    def __init__(self, bucket_name: str, region: str = 'ap-south-1'):
        """
        Initialize the stock data client
        
        Args:
            bucket_name: S3 bucket name (e.g., 'stock-pipeline-dev-ohlcv-a1b2c3d4')
            region: AWS region (default: 'ap-south-1')
        """
        self.s3 = boto3.client('s3', region_name=region)
        self.bucket = bucket_name
        self.region = region
    
    def get_latest_price(self, symbol: str) -> Optional[Dict]:
        """
        Get the latest price for a symbol
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE', 'TCS')
            
        Returns:
            Dictionary with latest price data or None if not found
        """
        key = f"latest/{symbol}_latest.json"
        return self._get_json_object(key)
    
    def get_latest_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get latest prices for multiple symbols
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbol to price data
        """
        result = {}
        for symbol in symbols:
            data = self.get_latest_price(symbol)
            if data:
                result[symbol] = data
        return result
    
    def get_historical_data(self, symbol: str, date: datetime, hour: Optional[int] = None) -> Union[Dict, List[Dict]]:
        """
        Get historical data for a specific date/hour
        
        Args:
            symbol: Stock symbol
            date: Date to fetch data for
            hour: Specific hour (0-23), if None returns all hours for the day
            
        Returns:
            Single data point (if hour specified) or list of data points
        """
        year, month, day = date.strftime('%Y'), date.strftime('%m'), date.strftime('%d')
        
        if hour is not None:
            # Get specific hour
            key = f"year={year}/month={month}/day={day}/hour={hour:02d}/{symbol}_{date.strftime('%Y%m%d')}_{hour:02d}15.json"
            return self._get_json_object(key)
        else:
            # Get all data for the day
            prefix = f"year={year}/month={month}/day={day}/"
            files = self._list_files(prefix, symbol)
            return [self._get_json_object(f) for f in files if self._get_json_object(f)]
    
    def get_price_range(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Get price data for a date range
        
        Args:
            symbol: Stock symbol
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of price data points
        """
        all_data = []
        current_date = start_date
        
        while current_date <= end_date:
            daily_data = self.get_historical_data(symbol, current_date)
            if isinstance(daily_data, list):
                all_data.extend(daily_data)
            elif daily_data:
                all_data.append(daily_data)
            current_date += timedelta(days=1)
        
        return sorted(all_data, key=lambda x: x['timestamp'])
    
    def to_dataframe(self, data: Union[Dict, List[Dict]]) -> pd.DataFrame:
        """
        Convert price data to pandas DataFrame
        
        Args:
            data: Single data point or list of data points
            
        Returns:
            pandas DataFrame with OHLCV data
        """
        if isinstance(data, dict):
            data = [data]
        
        rows = []
        for item in data:
            row = {
                'symbol': item['symbol'],
                'timestamp': pd.to_datetime(item['timestamp']),
                'open': item['ohlcv']['open'],
                'high': item['ohlcv']['high'],
                'low': item['ohlcv']['low'],
                'close': item['ohlcv']['close'],
                'volume': item['ohlcv']['volume']
            }
            
            # Add technical indicators if available
            if 'technical_indicators' in item:
                for key, value in item['technical_indicators'].items():
                    row[key] = value
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        if not df.empty:
            df.set_index('timestamp', inplace=True)
        return df
    
    def _get_json_object(self, key: str) -> Optional[Dict]:
        """Get and parse JSON object from S3"""
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            return json.loads(response['Body'].read())
        except Exception as e:
            # print(f"Error fetching {key}: {e}")
            return None
    
    def _list_files(self, prefix: str, symbol: str) -> List[str]:
        """List files matching prefix and symbol"""
        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [obj['Key'] for obj in response.get('Contents', []) 
                    if symbol in obj['Key'] and obj['Key'].endswith('.json')]
        except Exception as e:
            # print(f"Error listing files: {e}")
            return []


class RealTimeStockStream:
    """Client for real-time stock data notifications"""
    
    def __init__(self, topic_arn: str, region: str = 'ap-south-1'):
        """
        Initialize the real-time stream client
        
        Args:
            topic_arn: SNS topic ARN for notifications
            region: AWS region
        """
        self.sns = boto3.client('sns', region_name=region)
        self.topic_arn = topic_arn
    
    def subscribe_email(self, email: str) -> str:
        """
        Subscribe to email notifications
        
        Args:
            email: Email address to subscribe
            
        Returns:
            Subscription ARN
        """
        response = self.sns.subscribe(
            TopicArn=self.topic_arn,
            Protocol='email',
            Endpoint=email
        )
        return response['SubscriptionArn']
    
    def subscribe_sqs(self, queue_arn: str) -> str:
        """
        Subscribe SQS queue to notifications
        
        Args:
            queue_arn: SQS queue ARN
            
        Returns:
            Subscription ARN
        """
        response = self.sns.subscribe(
            TopicArn=self.topic_arn,
            Protocol='sqs',
            Endpoint=queue_arn
        )
        return response['SubscriptionArN']
    
    def unsubscribe(self, subscription_arn: str):
        """
        Unsubscribe from notifications
        
        Args:
            subscription_arn: Subscription ARN to remove
        """
        self.sns.unsubscribe(SubscriptionArn=subscription_arn)


# Example usage and utilities
def get_market_status() -> Dict[str, str]:
    """Check if market is currently open"""
    import pytz
    
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Market hours: 9:15 AM to 3:30 PM IST, Monday to Friday
    if now.weekday() >= 5:  # Weekend
        return {"status": "closed", "reason": "weekend"}
    
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if now < market_open:
        return {"status": "pre_market", "opens_at": market_open.isoformat()}
    elif now > market_close:
        return {"status": "closed", "closed_at": market_close.isoformat()}
    else:
        return {"status": "open", "closes_at": market_close.isoformat()}


if __name__ == "__main__":
    # Example usage
    import os
    
    # Initialize client
    bucket_name = os.getenv('STOCK_DATA_BUCKET', 'stock-pipeline-dev-ohlcv-a1b2c3d4')
    client = StockDataClient(bucket_name)
    
    # Get latest prices
    print("=== Latest Prices ===")
    symbols = ['RELIANCE', 'TCS', 'INFY']
    latest_prices = client.get_latest_prices(symbols)
    
    for symbol, data in latest_prices.items():
        if data:
            price = data['ohlcv']['close']
            volume = data['ohlcv']['volume']
            print(f"{symbol}: ₹{price:,.2f} (Volume: {volume:,})")
    
    # Get historical data and convert to DataFrame
    print("\n=== Historical Data (Last 3 days) ===")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)
    
    historical = client.get_price_range('RELIANCE', start_date, end_date)
    if historical:
        df = client.to_dataframe(historical)
        print(df.tail())
        
        # Basic analysis
        print(f"\nPrice Analysis for RELIANCE:")
        print(f"Max Price: ₹{df['high'].max():,.2f}")
        print(f"Min Price: ₹{df['low'].min():,.2f}")
        print(f"Avg Volume: {df['volume'].mean():,.0f}")
    
    # Check market status
    print(f"\n=== Market Status ===")
    status = get_market_status()
    print(f"Status: {status['status']}")
