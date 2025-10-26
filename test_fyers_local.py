#!/usr/bin/env python3
"""
Test Fyers API locally using your working approach
"""

import os
import time
import pandas as pd
from datetime import datetime

try:
    from fyers_apiv3 import fyersModel
    print("✅ fyers_apiv3 package is available")
except ImportError:
    print("❌ fyers_apiv3 package not found. Install with: pip install fyers-apiv3")
    exit(1)

# Your working config
CLIENT_ID = "OZXY8FPH1Q-100"
DATE_STR = "2025-09-03"  # Today's date
RESOLUTION = "5"
DATE_FORMAT = "1"

# Test symbols (subset for quick test)
TEST_SYMBOLS = [
    ("Reliance", "NSE:RELIANCE-EQ"),
    ("TCS", "NSE:TCS-EQ"),
    ("HDFC_Bank", "NSE:HDFCBANK-EQ"),
]

def main():
    print("🔗 Paste your FYERS access token and press Enter:")
    access_token = input().strip()
    
    if not access_token:
        print("❌ No token provided. Exiting.")
        return

    # Initialize client (your working approach)
    try:
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=access_token, log_path="")
        print("✅ Fyers client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Fyers client: {e}")
        return

    print(f"\n🔍 Testing with {len(TEST_SYMBOLS)} symbols for {DATE_STR}...")

    for friendly, symbol in TEST_SYMBOLS:
        try:
            print(f"\n📊 Testing {friendly} ({symbol})...")
            
            payload = {
                "symbol": symbol,
                "resolution": RESOLUTION,
                "date_format": DATE_FORMAT,
                "range_from": DATE_STR,
                "range_to": DATE_STR,
                "cont_flag": "1"
            }

            print(f"   📤 Sending request: {payload}")
            resp = fyers.history(payload)
            print(f"   📥 Response type: {type(resp)}")
            
            if not isinstance(resp, dict):
                print(f"   ❌ Unexpected response type: {type(resp)}")
                continue
                
            print(f"   📋 Response keys: {list(resp.keys()) if resp else 'None'}")
            
            if resp.get("s") == "error" or (resp.get("code") and resp.get("code") != 200):
                print(f"   ❌ API Error: {resp}")
                continue

            candles = resp.get("candles", [])
            print(f"   📈 Candles received: {len(candles)}")
            
            if candles:
                print(f"   ✅ SUCCESS: {len(candles)} candles for {friendly}")
                # Show first candle as sample
                if len(candles) > 0:
                    first_candle = candles[0]
                    print(f"   📊 Sample candle: {first_candle}")
            else:
                print(f"   ⚠️  No candles for {friendly}")

        except Exception as e:
            print(f"   ❌ Exception for {friendly}: {e}")
            import traceback
            traceback.print_exc()

        time.sleep(0.3)  # Rate limiting

    print("\n🎯 Test completed!")

if __name__ == "__main__":
    main()
