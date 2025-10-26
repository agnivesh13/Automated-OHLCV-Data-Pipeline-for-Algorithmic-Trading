#!/usr/bin/env python3
"""
Intercept and log what fyers_apiv3 actually does
"""

import requests
from fyers_apiv3 import fyersModel
import unittest.mock

# Patch requests to see what the package actually calls
original_request = requests.request

def logged_request(*args, **kwargs):
    print(f"🔍 INTERCEPTED REQUEST:")
    print(f"   Method: {args[0] if args else kwargs.get('method', 'Unknown')}")
    print(f"   URL: {args[1] if len(args) > 1 else kwargs.get('url', 'Unknown')}")
    print(f"   Headers: {kwargs.get('headers', {})}")
    print(f"   Params: {kwargs.get('params', {})}")
    print(f"   Data: {kwargs.get('data', kwargs.get('json', {}))}")
    print("=" * 50)
    
    # Call the original request
    return original_request(*args, **kwargs)

# Monkey patch requests
requests.request = logged_request
requests.get = lambda *args, **kwargs: logged_request('GET', *args, **kwargs)
requests.post = lambda *args, **kwargs: logged_request('POST', *args, **kwargs)

# Your working credentials
CLIENT_ID = "OZXY8FPH1Q-100"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiZDoxIiwiZDoyIiwieDowIiwieDoxIiwieDoyIl0sImF0X2hhc2giOiJnQUFBQUFCb3VFbTFiVktPNk1qN1hzdGFpZEtwdUNuQTlBUXdLX0hzZTdhdmJBSkZQam5RLTY5UFZQTktNbTRmZVVWeThWcnY0czYyMVJ1TXBSdDAyMVlSb1R1alhaTFBkWS1QMDF4NWgyRVk1VVZjdWFhbU5wQT0iLCJkaXNwbGF5X25hbWUiOiIiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiJhOTlmZWJmNzVhYWY4NjNkMGFhNmJkOTYxZTY2ZTIzODBmOWE3NDRiZGVlZGJiNWVkMWI2YzJiNCIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImZ5X2lkIjoiWFM5MTU5MSIsImFwcFR5cGUiOjEwMCwiZXhwIjoxNzU2OTQ1ODAwLCJpYXQiOjE3NTY5MDc5NTcsImlzcyI6ImFwaS5meWVycy5pbiIsIm5iZiI6MTc1NjkwNzk1Nywic3ViIjoiYWNjZXNzX3Rva2VuIn0.RoBoM8apPk8P6NgaafEC8RxbfPUIO3KRDCVB3xsQKVI"

def main():
    print("🕵️ Intercepting fyers_apiv3 network calls...")
    
    try:
        # Initialize client
        print("\n📱 Initializing Fyers client...")
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, log_path="")
        
        # Make a simple call
        print("\n📊 Making history() call...")
        payload = {
            "symbol": "NSE:RELIANCE-EQ",
            "resolution": "5",
            "date_format": "1", 
            "range_from": "2025-09-03",
            "range_to": "2025-09-03",
            "cont_flag": "1"
        }
        
        resp = fyers.history(payload)
        print(f"\n✅ Response received: {len(resp.get('candles', []))} candles")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
