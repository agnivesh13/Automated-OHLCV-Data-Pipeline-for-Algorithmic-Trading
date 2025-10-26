#!/usr/bin/env python3
"""
Simple Flask web dashboard to display OHLCV data
Usage: python dashboard.py
Then open: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify
import boto3
import json
from datetime import datetime, timedelta
import os

app = Flask(__name__)

def get_s3_client():
    return boto3.client('s3', region_name='ap-south-1')

def get_bucket_name():
    """Try to get bucket name from environment or Terraform output"""
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if not bucket_name:
        try:
            import subprocess
            result = subprocess.run(['terraform', 'output', '-raw', 's3_bucket_name'], 
                                  capture_output=True, text=True, cwd='../infra')
            if result.returncode == 0:
                bucket_name = result.stdout.strip()
        except:
            pass
    
    # If still no bucket name, try to find it by listing S3 buckets
    if not bucket_name:
        try:
            import boto3
            s3 = boto3.client('s3', region_name='ap-south-1')
            response = s3.list_buckets()
            for bucket in response['Buckets']:
                if 'stock-pipeline-dev-ohlcv' in bucket['Name']:
                    bucket_name = bucket['Name']
                    print(f"Auto-detected bucket: {bucket_name}")
                    break
        except Exception as e:
            print(f"Could not auto-detect bucket: {e}")
    
    return bucket_name or "stock-pipeline-dev-ohlcv-XXXXXXXX"

def list_recent_data(bucket_name, limit=10):
    """List recent data files"""
    s3 = get_s3_client()
    
    try:
        print(f"🔍 DEBUG: Searching in bucket: {bucket_name}")
    raw_prefix = os.environ.get('S3_RAW_PREFIX', 'Raw data/Prices/')
    print(f"🔍 DEBUG: Looking for files with prefix: {raw_prefix}")

    # Look for raw data in configured prefix
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=raw_prefix)
        
        if 'Contents' not in response:
            print(f"⚠️  No files found in {raw_prefix} prefix, trying ohlcv/ prefix")
            # Fallback to old ohlcv prefix for backward compatibility
            response = s3.list_objects_v2(Bucket=bucket_name, Prefix="ohlcv/")
            
        if 'Contents' not in response:
            print("❌ No files found in either prefix")
            return []
        
        files = []
        for obj in response['Contents']:
            # Only include JSON files
            if obj['Key'].endswith('.json'):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'modified': obj['LastModified']
                })
        
        print(f"📁 DEBUG: Found {len(files)} JSON files total")
        
        # Sort by modification date (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        # Debug: show latest files
        print("📋 DEBUG: Latest 5 files:")
        for i, f in enumerate(files[:5]):
            print(f"   {i+1}. {f['key']} ({f['size']} bytes) - {f['modified']}")
        
        return files[:limit]
    
    except Exception as e:
        print(f"Error listing files: {e}")
        return []

def fetch_latest_data(bucket_name):
    """Fetch the most recent data file"""
    files = list_recent_data(bucket_name, 1)
    if not files:
        return None
    
    s3 = get_s3_client()
    try:
        response = s3.get_object(Bucket=bucket_name, Key=files[0]['key'])
        data = json.loads(response['Body'].read().decode('utf-8'))
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

@app.route('/')
def dashboard():
    bucket_name = get_bucket_name()
    
    # Get recent files
    recent_files = list_recent_data(bucket_name, 5)
    
    # Get latest data
    latest_data = fetch_latest_data(bucket_name)
    
    # Process data for display
    symbols_data = []
    metadata = {}
    
    if latest_data and 'data' in latest_data:
        metadata = latest_data.get('metadata', {})
        
        for symbol, values in latest_data['data'].items():
            if isinstance(values, dict):
                # Check if this is candles format (from mock data) or direct OHLCV format
                if 'candles' in values and values['candles']:
                    # Extract latest candle data: [timestamp, open, high, low, close, volume]
                    latest_candle = values['candles'][-1]  # Most recent candle
                    open_price = round(latest_candle[1], 2)
                    high_price = round(latest_candle[2], 2)
                    low_price = round(latest_candle[3], 2)
                    close_price = round(latest_candle[4], 2)
                    volume = int(latest_candle[5])
                    
                    # Calculate change (close - open)
                    change = round(close_price - open_price, 2)
                    change_percent = round((change / open_price * 100), 2) if open_price > 0 else 0
                    
                    symbols_data.append({
                        'symbol': symbol,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume,
                        'change': change,
                        'change_percent': change_percent
                    })
                else:
                    # Original format
                    symbols_data.append({
                        'symbol': symbol,
                        'open': values.get('o', 'N/A'),
                        'high': values.get('h', 'N/A'),
                        'low': values.get('l', 'N/A'),
                        'close': values.get('ltp', values.get('c', 'N/A')),
                        'volume': values.get('v', 'N/A'),
                        'change': values.get('ch', 'N/A'),
                        'change_percent': values.get('chp', 'N/A')
                    })
    
    return render_template('dashboard.html', 
                         symbols=symbols_data, 
                         metadata=metadata,
                         recent_files=recent_files,
                         bucket_name=bucket_name)

@app.route('/api/data')
def api_data():
    bucket_name = get_bucket_name()
    data = fetch_latest_data(bucket_name)
    return jsonify(data) if data else jsonify({'error': 'No data available'})

@app.route('/files')
def files_view():
    """Show all data files for browsing"""
    bucket_name = get_bucket_name()
    all_files = list_recent_data(bucket_name, 50)  # Get more files
    
    return render_template('files.html', 
                         files=all_files, 
                         bucket_name=bucket_name)

@app.route('/')
def index():
    """Main page showing recent data files"""
    files = list_recent_data()
    print(f"🏠 DEBUG: Found {len(files)} files for main page")
    return render_template('files.html', files=files)

@app.route('/test')
def test():
    """Simple test route"""
    return "<h1>Flask is working!</h1><p>This is a test page.</p>"

@app.route('/file/<path:file_key>')
def file_detail(file_key):
    """Show detailed data for a specific file"""
    bucket_name = get_bucket_name()
    
    print(f"🔍 DEBUG: Requested file_key: {file_key}")
    print(f"🔍 DEBUG: Bucket name: {bucket_name}")
    
    try:
        s3 = get_s3_client()
        print(f"📁 DEBUG: Attempting to fetch object from S3...")
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        print(f"✅ DEBUG: Successfully fetched object, size: {len(response['Body'].read())} bytes")
        
        # Reset the stream position
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        data = json.loads(response['Body'].read().decode('utf-8'))
        
        print(f"📊 DEBUG: Parsed JSON successfully")
        
        # Process data for detailed view
        symbols_detail = []
        metadata = data.get('metadata', {})
        
        # Handle both old mock format (data.data) and new real API format (direct symbols)
        if 'data' in data and isinstance(data['data'], dict):
            # Old mock data format
            data_source = data['data']
            print(f"🔍 DEBUG: Processing old format - Found {len(data_source)} symbols in data.data")
        else:
            # New real API format - symbols are directly in the JSON
            data_source = {k: v for k, v in data.items() if k != 'metadata'}
            print(f"🔍 DEBUG: Processing new format - Found {len(data_source)} symbols directly in data")
        
        for symbol, values in data_source.items():
            if isinstance(values, dict):
                # Handle both 'candles' (old format) and 'candles_sample' (new format)
                candles_data = values.get('candles') or values.get('candles_sample', [])
                
                # Convert candle arrays to objects that template expects
                # Format: [timestamp, open, high, low, close, volume]
                processed_candles = []
                for candle in candles_data:
                    if isinstance(candle, list) and len(candle) >= 6:
                        # Convert Unix timestamp to readable datetime
                        from datetime import datetime
                        dt = datetime.fromtimestamp(candle[0])
                        formatted_time = dt.strftime('%H:%M:%S')
                        
                        candle_obj = {
                            'timestamp': candle[0],
                            'datetime': formatted_time,  # Add formatted time for display
                            'open': candle[1],
                            'high': candle[2], 
                            'low': candle[3],
                            'close': candle[4],
                            'volume': candle[5]
                        }
                        processed_candles.append(candle_obj)
                
                symbol_info = {
                    'symbol': values.get('symbol', symbol),
                    'total_candles': values.get('total_candles', len(candles_data)),
                    'resolution': values.get('resolution', 'Unknown'),
                    'latest_price': values.get('latest_price') or (candles_data[0][4] if candles_data else 0),
                    'timestamp': values.get('timestamp', 'Unknown'),
                    'candles': processed_candles  # Template expects 'candles'
                }
                symbols_detail.append(symbol_info)
        
        print(f"✅ DEBUG: Processed {len(symbols_detail)} symbols for display")
        
        # Debug: Print first symbol structure to understand the data format
        if symbols_detail:
            first_symbol = symbols_detail[0]
            print(f"🔍 DEBUG: First symbol keys: {list(first_symbol.keys())}")
            print(f"🔍 DEBUG: First symbol sample candle: {first_symbol['candles'][0] if first_symbol['candles'] else 'No candles'}")
        
        return render_template('file_detail.html', 
                             symbols=symbols_detail,
                             metadata=metadata,
                             file_key=file_key)
    
    except Exception as e:
        print(f"❌ DEBUG ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"<h1>Error loading file</h1><p>Error: {str(e)}</p><p>File: {file_key}</p>", 500
        
        for symbol, values in data.get('data', {}).items():
            if isinstance(values, dict) and 'candles' in values:
                # Process candle data for chart display
                candles_processed = []
                for candle in values['candles']:
                    candles_processed.append({
                        'timestamp': candle[0],
                        'datetime': datetime.fromtimestamp(candle[0]).strftime('%H:%M:%S'),
                        'open': round(candle[1], 2),
                        'high': round(candle[2], 2),
                        'low': round(candle[3], 2),
                        'close': round(candle[4], 2),
                        'volume': int(candle[5])
                    })
                
                symbols_detail.append({
                    'symbol': symbol,
                    'candles': candles_processed,
                    'total_candles': len(candles_processed)
                })
        
        return render_template('file_detail.html',
                             file_key=file_key,
                             symbols=symbols_detail,
                             metadata=metadata,
                             bucket_name=bucket_name)
                             
    except Exception as e:
        return f"Error loading file: {e}", 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
