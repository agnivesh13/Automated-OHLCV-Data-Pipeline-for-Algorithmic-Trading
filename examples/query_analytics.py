"""
Example queries for Analytics Lambda
Demonstrates how to invoke Lambda analytics functions

Usage:
    python query_analytics.py
"""

import boto3
import json
from datetime import datetime, timedelta

# Initialize Lambda client
lambda_client = boto3.client('lambda', region_name='ap-south-1')

# Lambda function name (update after deployment)
FUNCTION_NAME = 'stock-pipeline-dev-analytics'


def invoke_analytics(query_type, **kwargs):
    """
    Invoke analytics Lambda with query parameters
    
    Args:
        query_type: Type of query (symbol_stats, daily_summary, date_range, top_movers)
        **kwargs: Additional query parameters
    
    Returns:
        Query results as dictionary
    """
    payload = {
        'query_type': query_type,
        **kwargs
    }
    
    print(f"\n{'='*70}")
    print(f"Query: {query_type}")
    print(f"Parameters: {json.dumps(kwargs, indent=2)}")
    print(f"{'='*70}")
    
    try:
        # Invoke Lambda
        response = lambda_client.invoke(
            FunctionName=FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        if response_payload.get('statusCode') == 200:
            result = json.loads(response_payload['body'])
            print(f"\n✓ SUCCESS")
            print(json.dumps(result, indent=2))
            return result
        else:
            error = json.loads(response_payload['body'])
            print(f"\n✗ ERROR: {error.get('error', 'Unknown error')}")
            return None
    
    except Exception as e:
        print(f"\n✗ EXCEPTION: {str(e)}")
        return None


def example_symbol_stats():
    """Example 1: Get statistics for a single symbol on a date"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Symbol Statistics")
    print("="*70)
    print("Get OHLCV stats for RELIANCE on 2025-10-07")
    
    result = invoke_analytics(
        query_type='symbol_stats',
        symbol='RELIANCE',
        date='2025-10-07'
    )
    
    if result:
        stats = result['stats']
        print(f"\n📊 RELIANCE Summary:")
        print(f"   Open:         ₹{stats['open']:,.2f}")
        print(f"   Close:        ₹{stats['close']:,.2f}")
        print(f"   High:         ₹{stats['high']:,.2f}")
        print(f"   Low:          ₹{stats['low']:,.2f}")
        print(f"   Volume:       {stats['volume']:,}")
        print(f"   Change:       ₹{stats['price_change']:+.2f} ({stats['price_change_pct']:+.2f}%)")
        print(f"   Records:      {stats['num_records']}")


def example_daily_summary():
    """Example 2: Get summary for all symbols on a date"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Daily Market Summary")
    print("="*70)
    print("Get performance summary for all symbols on 2025-10-07")
    
    result = invoke_analytics(
        query_type='daily_summary',
        date='2025-10-07'
    )
    
    if result:
        print(f"\n📈 Market Summary ({result['total_symbols']} symbols):")
        print(f"\n{'Symbol':<15} {'Close':>10} {'Change %':>10} {'Volume':>15}")
        print("-" * 55)
        
        for stock in result['summary'][:10]:  # Show top 10
            print(f"{stock['symbol']:<15} ₹{stock['close']:>9,.2f} "
                  f"{stock['price_change_pct']:>9.2f}% {stock['volume']:>15,}")


def example_date_range():
    """Example 3: Get data for a symbol over date range"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Date Range Query")
    print("="*70)
    print("Get RELIANCE data for Oct 1-7, 2025")
    
    result = invoke_analytics(
        query_type='date_range',
        symbol='RELIANCE',
        start_date='2025-10-01',
        end_date='2025-10-07'
    )
    
    if result:
        print(f"\n📅 RELIANCE - {result['num_days']} trading days:")
        print(f"\n{'Date':<12} {'Open':>10} {'Close':>10} {'High':>10} {'Low':>10} {'Change %':>10}")
        print("-" * 67)
        
        for day in result['data']:
            print(f"{day['date']:<12} ₹{day['open']:>9,.2f} ₹{day['close']:>9,.2f} "
                  f"₹{day['high']:>9,.2f} ₹{day['low']:>9,.2f} {day['price_change_pct']:>9.2f}%")


def example_top_movers():
    """Example 4: Get top gainers/losers for a date"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Top Movers")
    print("="*70)
    print("Get top 5 gainers and losers on 2025-10-07")
    
    result = invoke_analytics(
        query_type='top_movers',
        date='2025-10-07',
        limit=5
    )
    
    if result:
        print(f"\n🚀 TOP 5 GAINERS:")
        print(f"{'Symbol':<15} {'Change %':>10} {'Close':>10} {'Volume':>15}")
        print("-" * 55)
        for stock in result['gainers']:
            print(f"{stock['symbol']:<15} {stock['price_change_pct']:>9.2f}% "
                  f"₹{stock['close']:>9,.2f} {stock['volume']:>15,}")
        
        print(f"\n📉 TOP 5 LOSERS:")
        print(f"{'Symbol':<15} {'Change %':>10} {'Close':>10} {'Volume':>15}")
        print("-" * 55)
        for stock in result['losers']:
            print(f"{stock['symbol']:<15} {stock['price_change_pct']:>9.2f}% "
                  f"₹{stock['close']:>9,.2f} {stock['volume']:>15,}")


def example_programmatic_analysis():
    """Example 5: Programmatic analysis - find volatile stocks"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Custom Analysis - High Volatility Stocks")
    print("="*70)
    print("Find stocks with >2% price movement")
    
    # Get daily summary
    result = invoke_analytics(
        query_type='daily_summary',
        date='2025-10-07'
    )
    
    if result:
        # Filter volatile stocks
        volatile = [
            s for s in result['summary']
            if abs(s['price_change_pct']) > 2.0
        ]
        
        print(f"\n⚡ Found {len(volatile)} volatile stocks (>2% movement):")
        print(f"\n{'Symbol':<15} {'Change %':>10} {'Close':>10} {'Volume':>15}")
        print("-" * 55)
        
        # Sort by absolute change
        volatile.sort(key=lambda x: abs(x['price_change_pct']), reverse=True)
        
        for stock in volatile[:10]:
            print(f"{stock['symbol']:<15} {stock['price_change_pct']:>9.2f}% "
                  f"₹{stock['close']:>9,.2f} {stock['volume']:>15,}")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("AWS LAMBDA ANALYTICS - QUERY EXAMPLES")
    print("="*70)
    print(f"Function: {FUNCTION_NAME}")
    print(f"Region: ap-south-1")
    print("="*70)
    
    try:
        # Run examples
        example_symbol_stats()
        example_daily_summary()
        example_date_range()
        example_top_movers()
        example_programmatic_analysis()
        
        print("\n" + "="*70)
        print("✓ ALL EXAMPLES COMPLETED")
        print("="*70)
        print("\nCost Analysis:")
        print("  Queries executed: 5")
        print("  Lambda invocations: 5")
        print("  S3 GET requests: ~35 (reading CSV files)")
        print("  Lambda compute: ~10 GB-seconds")
        print("  Estimated cost: $0.00 (within free tier)")
        print("="*70)
    
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")


if __name__ == '__main__':
    main()
