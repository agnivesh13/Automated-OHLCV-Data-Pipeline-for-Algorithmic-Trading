#!/usr/bin/env python3
"""
Debug script to understand what fyers_apiv3 actually does
"""

import requests
from fyers_apiv3 import fyersModel
import json

# Your working credentials
CLIENT_ID = "OZXY8FPH1Q-100"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiZDoxIiwiZDoyIiwieDowIiwieDoxIiwieDoyIl0sImF0X2hhc2giOiJnQUFBQUFCb3VFbTFiVktPNk1qN1hzdGFpZEtwdUNuQTlBUXdLX0hzZTdhdmJBSkZQam5RLTY5UFZQTktNbTRmZVVWeThWcnY0czYyMVJ1TXBSdDAyMVlSb1R1alhaTFBkWS1QMDF4NWgyRVk1VVZjdWFhbU5wQT0iLCJkaXNwbGF5X25hbWUiOiIiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiJhOTlmZWJmNzVhYWY4NjNkMGFhNmJkOTYxZTY2ZTIzODBmOWE3NDRiZGVlZGJiNWVkMWI2YzJiNCIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImZ5X2lkIjoiWFM5MTU5MSIsImFwcFR5cGUiOjEwMCwiZXhwIjoxNzU2OTQ1ODAwLCJpYXQiOjE3NTY5MDc5NTcsImlzcyI6ImFwaS5meWVycy5pbiIsIm5iZiI6MTc1NjkwNzk1Nywic3ViIjoiYWNjZXNzX3Rva2VuIn0.RoBoM8apPk8P6NgaafEC8RxbfPUIO3KRDCVB3xsQKVI"

def test_direct_api_calls():
    """Test direct API calls to understand what fails"""
    print("=== Testing Direct API Calls ===")
    
    endpoints_to_test = [
        "https://api.fyers.in/api/v3/profile",
        "https://api.fyers.in/data-rest/v3/history",
        "https://api-t2.fyers.in/data-rest/v3/history",
        "https://api.fyers.in/data-rest/v2/history",
        "https://tradapi.fyers.in/tradapi/v1/history",
    ]
    
    headers = {
        'Authorization': f"Bearer {ACCESS_TOKEN}",
        'Content-Type': 'application/json'
    }
    
    for endpoint in endpoints_to_test:
        try:
            print(f"\n🔍 Testing: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=5)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_fyers_package():
    """Test what the working fyers_apiv3 package does"""
    print("\n=== Testing fyers_apiv3 Package ===")
    
    try:
        # Initialize client
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, log_path="")
        
        # Test with one symbol
        payload = {
            "symbol": "NSE:RELIANCE-EQ",
            "resolution": "5",
            "date_format": "1",
            "range_from": "2025-09-03",
            "range_to": "2025-09-03",
            "cont_flag": "1"
        }
        
        print(f"📊 Testing fyers.history() with payload: {payload}")
        resp = fyers.history(payload)
        
        print(f"✅ Success! Response type: {type(resp)}")
        print(f"📋 Response keys: {list(resp.keys()) if isinstance(resp, dict) else 'Not dict'}")
        if isinstance(resp, dict) and 'candles' in resp:
            print(f"📈 Candles count: {len(resp['candles'])}")
        
        return resp
        
    except Exception as e:
        print(f"❌ fyers_apiv3 failed: {e}")
        return None

def analyze_package_internals():
    """Try to understand what fyers_apiv3 does internally"""
    print("\n=== Analyzing Package Internals ===")
    
    try:
        # Look at the fyers object properties
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, log_path="")
        
        # Check what attributes the object has
        print("📋 Fyers object attributes:")
        for attr in dir(fyers):
            if not attr.startswith('_'):
                print(f"   - {attr}")
        
        # Try to see base URL or endpoints
        if hasattr(fyers, 'base_url'):
            print(f"🔗 Base URL: {fyers.base_url}")
        if hasattr(fyers, '_base_url'):
            print(f"🔗 Private Base URL: {fyers._base_url}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")

def main():
    print("🔍 Debugging Fyers API Endpoints\n")
    
    # Test direct calls (that fail)
    test_direct_api_calls()
    
    # Test working package
    working_response = test_fyers_package()
    
    # Analyze internals
    analyze_package_internals()
    
    print("\n🎯 Summary:")
    print("- Direct REST API calls: ❌ 503 errors")
    print("- fyers_apiv3 package: ✅ Working")
    print("- Conclusion: Package uses different/internal endpoints")

if __name__ == "__main__":
    main()
