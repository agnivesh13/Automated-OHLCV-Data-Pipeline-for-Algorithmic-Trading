"""
Quick Start Example for Stock Data API
Demonstrates basic usage patterns for other teams
"""

import os
import json
from datetime import datetime, timedelta
from stock_client import StockDataClient, RealTimeStockStream, get_market_status

def main():
    """Quick start example showing common usage patterns"""
    
    print("🚀 Stock Data API - Quick Start Example")
    print("=" * 50)
    
    # 1. Setup - Get configuration from environment
    bucket_name = os.getenv('STOCK_DATA_BUCKET')
    sns_topic_arn = os.getenv('SNS_TOPIC_ARN')
    
    if not bucket_name:
        print("❌ Error: STOCK_DATA_BUCKET environment variable not set")
    print("Please set: export STOCK_DATA_BUCKET='stock-pipeline-dev-ohlcv-suffix'")
        return
    
    print(f"📊 Connected to bucket: {bucket_name}")
    
    # Initialize client
    client = StockDataClient(bucket_name)
    
    # 2. Check market status
    market_status = get_market_status()
    print(f"🏪 Market Status: {market_status['status'].upper()}")
    
    # 3. Get latest prices for popular stocks
    print("\n📈 Latest Stock Prices")
    print("-" * 30)
    
    popular_stocks = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']
    latest_prices = client.get_latest_prices(popular_stocks)
    
    for symbol, data in latest_prices.items():
        if data:
            price = data['ohlcv']['close']
            volume = data['ohlcv']['volume']
            timestamp = data['timestamp']
            
            # Calculate time since last update
            last_update = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_diff = datetime.now() - last_update.replace(tzinfo=None)
            
            print(f"{symbol:10} ₹{price:8.2f} | Vol: {volume:10,} | {time_diff.seconds//60}m ago")
    
    # 4. Historical analysis example
    print("\n📊 Historical Analysis (RELIANCE - Last 3 Days)")
    print("-" * 50)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)
    
    historical_data = client.get_price_range('RELIANCE', start_date, end_date)
    if historical_data:
        # Convert to DataFrame for analysis
        df = client.to_dataframe(historical_data)
        
        if not df.empty:
            print(f"📅 Data Points: {len(df)}")
            print(f"💰 Price Range: ₹{df['low'].min():.2f} - ₹{df['high'].max():.2f}")
            print(f"📊 Avg Volume: {df['volume'].mean():,.0f}")
            print(f"📈 Price Change: {((df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100):+.2f}%")
            
            # Show recent data
            print(f"\nRecent Prices:")
            recent = df.tail(3)[['open', 'high', 'low', 'close', 'volume']]
            for idx, row in recent.iterrows():
                print(f"{idx.strftime('%H:%M')} | O:{row['open']:7.2f} H:{row['high']:7.2f} L:{row['low']:7.2f} C:{row['close']:7.2f}")
    
    # 5. Real-time notifications setup (if SNS topic available)
    if sns_topic_arn:
        print("\n🔔 Real-time Notifications")
        print("-" * 30)
        
        stream = RealTimeStockStream(sns_topic_arn)
        print(f"📢 SNS Topic: {sns_topic_arn}")
        print("To subscribe to notifications:")
        print(f"   stream.subscribe_email('your-email@company.com')")
    
    # 6. Integration examples
    print("\n🔧 Integration Examples")
    print("-" * 30)
    print("1. Trading Bot:")
    print("   monitor_prices(['RELIANCE', 'TCS'])")
    print("\n2. Price Alerts:")
    print("   set_price_alert('RELIANCE', 'above', 2500)")
    print("\n3. Data Export:")
    print("   export_to_csv(['RELIANCE', 'TCS'], '2025-08-29')")
    
    print(f"\n✅ Quick start complete! Check the examples/ folder for more code samples.")


def monitor_prices(symbols, threshold_change=2.0):
    """Example: Monitor stocks for significant price changes"""
    print(f"\n👀 Monitoring {symbols} for {threshold_change}% price changes...")
    
    client = StockDataClient(os.getenv('STOCK_DATA_BUCKET'))
    
    # Get baseline prices (from 1 hour ago)
    baseline = {}
    for symbol in symbols:
        # This is simplified - in real implementation, you'd get actual historical data
        latest = client.get_latest_price(symbol)
        if latest:
            baseline[symbol] = latest['ohlcv']['close']
    
    print("Baseline prices set. Use this in a loop to monitor changes.")
    return baseline


def set_price_alert(symbol, condition, threshold):
    """Example: Set up price alert"""
    print(f"🚨 Alert set: {symbol} {condition} ₹{threshold}")
    print("In a real implementation, this would:")
    print("1. Store alert in database")
    print("2. Check condition periodically")
    print("3. Send notification when triggered")


def export_to_csv(symbols, date_str):
    """Example: Export data to CSV"""
    client = StockDataClient(os.getenv('STOCK_DATA_BUCKET'))
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        all_data = []
        
        for symbol in symbols:
            data = client.get_historical_data(symbol, date)
            if isinstance(data, list):
                all_data.extend(data)
        
        if all_data:
            df = client.to_dataframe(all_data)
            filename = f"stock_data_{date_str}.csv"
            df.to_csv(filename)
            print(f"📁 Data exported to {filename}")
            return filename
    except Exception as e:
        print(f"❌ Export failed: {e}")
    
    return None


if __name__ == "__main__":
    # Set example environment variables if not set
    if not os.getenv('STOCK_DATA_BUCKET'):
    os.environ['STOCK_DATA_BUCKET'] = 'stock-pipeline-dev-ohlcv-example'
        print("⚠️  Using example bucket name. Set STOCK_DATA_BUCKET environment variable.")
    
    main()
    
    # Run additional examples
    print("\n" + "="*60)
    print("Additional Examples:")
    
    # Example 1: Price monitoring
    baseline = monitor_prices(['RELIANCE', 'TCS'], 1.5)
    
    # Example 2: Price alerts
    set_price_alert('RELIANCE', 'above', 2500)
    
    # Example 3: Data export
    export_to_csv(['RELIANCE', 'TCS'], '2025-08-29')
