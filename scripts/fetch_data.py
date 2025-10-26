#!/usr/bin/env python3
"""
Simple script to fetch and display OHLCV data from S3
Usage: python fetch_data.py [--date YYYY-MM-DD] [--symbol SYMBOL]
"""

import boto3
import json
import argparse
from datetime import datetime, timedelta
import pandas as pd

def get_s3_client():
    """Initialize S3 client"""
    return boto3.client('s3', region_name='ap-south-1')

def list_available_data(bucket_name, prefix="ohlcv/"):
    """List all available data files in S3"""
    s3 = get_s3_client()
    
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        
        if 'Contents' not in response:
            print("No data files found in S3 bucket")
            return []
        
        files = []
        for obj in response['Contents']:
            key = obj['Key']
            size = obj['Size']
            modified = obj['LastModified']
            files.append({
                'key': key,
                'size': f"{size:,} bytes",
                'modified': modified.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return files
    
    except Exception as e:
        print(f"Error listing S3 objects: {e}")
        return []

def fetch_data_from_s3(bucket_name, key):
    """Fetch specific data file from S3"""
    s3 = get_s3_client()
    
    try:
        response = s3.get_object(Bucket=bucket_name, Key=key)
        data = json.loads(response['Body'].read().decode('utf-8'))
        return data
    
    except Exception as e:
        print(f"Error fetching data from S3: {e}")
        return None

def display_data_summary(data):
    """Display a summary of the OHLCV data"""
    if not data or 'data' not in data:
        print("No valid data found")
        return
    
    ohlcv_data = data['data']
    metadata = data.get('metadata', {})
    
    print("\n" + "="*60)
    print("📊 OHLCV DATA SUMMARY")
    print("="*60)
    
    # Metadata
    print(f"📅 Timestamp: {metadata.get('timestamp', 'Unknown')}")
    print(f"📈 Total Symbols: {metadata.get('total_symbols_requested', 0)}")
    print(f"✅ Successful: {metadata.get('successful_symbols', 0)}")
    print(f"❌ Failed: {metadata.get('failed_symbols', 0)}")
    
    if not ohlcv_data:
        print("No OHLCV data available")
        return
    
    # Convert to DataFrame for better display
    df_data = []
    for symbol, values in ohlcv_data.items():
        if isinstance(values, dict):
            row = {'symbol': symbol}
            row.update(values)
            df_data.append(row)
    
    if df_data:
        df = pd.DataFrame(df_data)
        
        print(f"\n📋 OHLCV Data ({len(df)} symbols):")
        print("-" * 60)
        
        # Display top 10 symbols
        display_df = df.head(10)
        
        for _, row in display_df.iterrows():
            print(f"🏢 {row['symbol']:<12} | "
                  f"O: ₹{row.get('o', 'N/A'):<8} | "
                  f"H: ₹{row.get('h', 'N/A'):<8} | "
                  f"L: ₹{row.get('l', 'N/A'):<8} | "
                  f"C: ₹{row.get('ltp', row.get('c', 'N/A')):<8} | "
                  f"V: {row.get('v', 'N/A')}")
        
        if len(df) > 10:
            print(f"... and {len(df) - 10} more symbols")
        
        # Summary stats
        print(f"\n📊 Price Statistics:")
        print(f"   Highest Price: ₹{df['h'].max():.2f}" if 'h' in df.columns else "   Highest Price: N/A")
        print(f"   Lowest Price:  ₹{df['l'].min():.2f}" if 'l' in df.columns else "   Lowest Price: N/A")
        print(f"   Avg Volume:    {df['v'].mean():,.0f}" if 'v' in df.columns else "   Avg Volume: N/A")

def main():
    parser = argparse.ArgumentParser(description='Fetch OHLCV data from S3')
    parser.add_argument('--bucket', help='S3 bucket name')
    parser.add_argument('--date', help='Date in YYYY-MM-DD format')
    parser.add_argument('--symbol', help='Specific symbol to search for')
    parser.add_argument('--list', action='store_true', help='List all available files')
    
    args = parser.parse_args()
    
    # Try to get bucket name from Terraform output or user input
    bucket_name = args.bucket
    if not bucket_name:
        try:
            # Try to get from Terraform output
            import subprocess
            result = subprocess.run(['terraform', 'output', '-raw', 's3_bucket_name'], 
                                  capture_output=True, text=True, cwd='../infra')
            if result.returncode == 0:
                bucket_name = result.stdout.strip()
            else:
                bucket_name = input("Enter S3 bucket name: ").strip()
        except:
            bucket_name = input("Enter S3 bucket name: ").strip()
    
    if not bucket_name:
        print("Error: S3 bucket name is required")
        return
    
    print(f"🪣 Using S3 bucket: {bucket_name}")
    
    # List available files
    if args.list:
        print("\n📁 Available data files:")
        files = list_available_data(bucket_name)
        for file_info in files:
            print(f"   📄 {file_info['key']} ({file_info['size']}) - {file_info['modified']}")
        return
    
    # Get available files
    files = list_available_data(bucket_name)
    if not files:
        print("No data files found. Make sure the Lambda function has run and created data.")
        return
    
    # If date specified, look for that date
    if args.date:
        date_prefix = args.date.replace('-', '/')
        matching_files = [f for f in files if date_prefix in f['key']]
        if not matching_files:
            print(f"No data found for date {args.date}")
            return
        target_file = matching_files[0]['key']
    else:
        # Use the most recent file
        files.sort(key=lambda x: x['modified'], reverse=True)
        target_file = files[0]['key']
    
    print(f"📄 Fetching data from: {target_file}")
    
    # Fetch and display data
    data = fetch_data_from_s3(bucket_name, target_file)
    if data:
        display_data_summary(data)
    
    # Filter by symbol if specified
    if args.symbol and data and 'data' in data:
        symbol_data = data['data'].get(args.symbol.upper())
        if symbol_data:
            print(f"\n🎯 Data for {args.symbol.upper()}:")
            print(json.dumps(symbol_data, indent=2))
        else:
            print(f"Symbol {args.symbol.upper()} not found in data")

if __name__ == "__main__":
    main()
