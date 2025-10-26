#!/usr/bin/env python3
"""
Manual Fyers Token Generator
============================

This script helps you generate Fyers API tokens manually when needed:
1. Generate authorization URL for manual login
2. Extract access token and refresh token from callback
3. Update AWS SSM parameters with new tokens

Usage:
python manual_token_generator.py --step 1  # Generate auth URL
python manual_token_generator.py --step 2 --auth-code YOUR_AUTH_CODE  # Get tokens
python manual_token_generator.py --step 3 --access-token TOKEN --refresh-token TOKEN  # Update SSM
"""

import argparse
import hashlib
import json
import requests
import urllib.parse
import webbrowser
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import os
import sys

# Configuration
FYERS_BASE_URL = "https://api-t2.fyers.in"
REDIRECT_URI = "https://trade.fyers.in/api-login/redirect-to-app"

def load_config():
    """Load configuration from environment or prompt user"""
    config = {}
    
    # Try to get from environment first
    config['client_id'] = os.getenv('FYERS_CLIENT_ID')
    config['app_secret'] = os.getenv('FYERS_APP_SECRET')
    config['aws_profile'] = os.getenv('AWS_PROFILE', 'default')
    config['aws_region'] = os.getenv('AWS_REGION', 'ap-south-1')
    
    # If not in environment, prompt user
    if not config['client_id']:
        print("📝 Fyers API Configuration Required")
        print("=" * 50)
        config['client_id'] = input("Enter your Fyers Client ID: ").strip()
        
    if not config['app_secret']:
        config['app_secret'] = input("Enter your Fyers App Secret: ").strip()
    
    if not config['client_id'] or not config['app_secret']:
        print("❌ Error: Client ID and App Secret are required!")
        sys.exit(1)
    
    return config

def step1_generate_auth_url(config):
    """Step 1: Generate authorization URL for manual login"""
    print("🚀 Step 1: Generate Authorization URL")
    print("=" * 50)
    
    # Generate app hash
    app_id_hash = hashlib.sha256(f"{config['client_id']}:{config['app_secret']}".encode()).hexdigest()
    
    # Build authorization URL
    auth_params = {
        'client_id': config['client_id'],
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'state': 'sample_state'
    }
    
    auth_url = f"{FYERS_BASE_URL}/api/v3/generate-authcode?" + urllib.parse.urlencode(auth_params)
    
    print(f"📋 Your Authorization URL:")
    print(f"🔗 {auth_url}")
    print()
    print("📖 Instructions:")
    print("1. Click the URL above (or copy-paste it in your browser)")
    print("2. Login to your Fyers account")
    print("3. After successful login, you'll be redirected to a URL")
    print("4. Copy the 'auth_code' parameter from the redirect URL")
    print("5. Run: python manual_token_generator.py --step 2 --auth-code YOUR_AUTH_CODE")
    print()
    
    # Optional: Auto-open in browser
    try:
        open_browser = input("🌐 Open URL in browser automatically? (y/n): ").strip().lower()
        if open_browser in ['y', 'yes']:
            webbrowser.open(auth_url)
            print("✅ URL opened in browser")
    except Exception as e:
        print(f"⚠️ Could not open browser: {e}")
    
    print()
    print("🔄 Next Step: Run with --step 2 and your auth code")

def step2_get_tokens(config, auth_code):
    """Step 2: Exchange auth code for access and refresh tokens"""
    print("🔑 Step 2: Generate Access & Refresh Tokens")
    print("=" * 50)
    
    # Generate app hash
    app_id_hash = hashlib.sha256(f"{config['client_id']}:{config['app_secret']}".encode()).hexdigest()
    
    # Token request payload
    token_payload = {
        'grant_type': 'authorization_code',
        'appIdHash': app_id_hash,
        'code': auth_code
    }
    
    # Make token request
    token_url = f"{FYERS_BASE_URL}/vagator/v2/generate_access_token"
    headers = {'Content-Type': 'application/json'}
    
    print(f"📡 Making token request to: {token_url}")
    
    try:
        response = requests.post(token_url, json=token_payload, headers=headers, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📄 Response: {json.dumps(data, indent=2)}")
            
            if data.get('s') == 'ok':
                access_token = data.get('access_token')
                refresh_token = data.get('refresh_token')
                
                if access_token and refresh_token:
                    print("✅ Tokens generated successfully!")
                    print(f"🔐 Access Token: {access_token[:20]}...{access_token[-10:]}")
                    print(f"🔄 Refresh Token: {refresh_token[:20]}...{refresh_token[-10:]}")
                    
                    # Save to local file for convenience
                    token_data = {
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'generated_at': datetime.now().isoformat(),
                        'client_id': config['client_id']
                    }
                    
                    with open('fyers_tokens.json', 'w') as f:
                        json.dump(token_data, f, indent=2)
                    
                    print("💾 Tokens saved to: fyers_tokens.json")
                    print()
                    print("🔄 Next Step: Run with --step 3 to update AWS SSM")
                    print(f"Command: python manual_token_generator.py --step 3 --access-token {access_token} --refresh-token {refresh_token}")
                    
                    return access_token, refresh_token
                else:
                    print("❌ Error: Tokens not found in response")
            else:
                print(f"❌ Error: {data.get('message', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
    
    return None, None

def step3_update_ssm(config, access_token, refresh_token):
    """Step 3: Update AWS SSM parameters with new tokens"""
    print("☁️ Step 3: Update AWS SSM Parameters")
    print("=" * 50)
    
    try:
        # Initialize AWS SSM client
        session = boto3.Session(profile_name=config['aws_profile'])
        ssm_client = session.client('ssm', region_name=config['aws_region'])
        
        # SSM parameter names
        project_prefix = "stock-pipeline"  # Adjust if different
        access_token_param = f"/{project_prefix}/fyers/access_token"
        refresh_token_param = f"/{project_prefix}/fyers/refresh_token"
        client_id_param = f"/{project_prefix}/fyers/client_id"
        
        print(f"📡 Updating SSM parameters in region: {config['aws_region']}")
        print(f"🏷️ Parameter prefix: /{project_prefix}/fyers/")
        
        # Update access token
        print(f"🔐 Updating access token: {access_token_param}")
        ssm_client.put_parameter(
            Name=access_token_param,
            Value=access_token,
            Type='SecureString',
            Overwrite=True,
            Description=f"Fyers access token - updated {datetime.now().isoformat()}"
        )
        print("✅ Access token updated")
        
        # Update refresh token
        print(f"🔄 Updating refresh token: {refresh_token_param}")
        ssm_client.put_parameter(
            Name=refresh_token_param,
            Value=refresh_token,
            Type='SecureString',
            Overwrite=True,
            Description=f"Fyers refresh token - updated {datetime.now().isoformat()}"
        )
        print("✅ Refresh token updated")
        
        # Update client ID (for consistency)
        print(f"🆔 Updating client ID: {client_id_param}")
        ssm_client.put_parameter(
            Name=client_id_param,
            Value=config['client_id'],
            Type='SecureString',
            Overwrite=True,
            Description=f"Fyers client ID - updated {datetime.now().isoformat()}"
        )
        print("✅ Client ID updated")
        
        print()
        print("🎉 All SSM parameters updated successfully!")
        print()
        print("🧪 Testing token validity...")
        
        # Test the tokens
        test_success = test_token_validity(config['client_id'], access_token)
        
        if test_success:
            print("✅ Token validation successful!")
            print("🚀 Your system is ready to run automatically!")
        else:
            print("⚠️ Token validation failed - please check the tokens")
            
    except ClientError as e:
        print(f"❌ AWS Error: {e}")
        print("💡 Make sure you have:")
        print("   - Correct AWS credentials configured")
        print("   - SSM permissions")
        print("   - Correct region selected")
    except Exception as e:
        print(f"❌ Error updating SSM: {e}")

def test_token_validity(client_id, access_token):
    """Test if the generated token is valid"""
    try:
        # Test with a simple API call
        test_url = "https://api-t1.fyers.in/api/v3/profile"
        headers = {
            'Authorization': f"{client_id}:{access_token}"
        }
        
        response = requests.get(test_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('s') == 'ok':
                print(f"📊 Profile: {data.get('data', {}).get('name', 'Unknown')}")
                return True
        
        print(f"🔍 Test response: {response.status_code} - {response.text[:200]}")
        return False
        
    except Exception as e:
        print(f"⚠️ Token test failed: {e}")
        return False

def refresh_existing_token(config):
    """Refresh an existing refresh token to get new access token"""
    print("🔄 Refresh Existing Token")
    print("=" * 50)
    
    # Try to get refresh token from SSM first
    try:
        session = boto3.Session(profile_name=config['aws_profile'])
        ssm_client = session.client('ssm', region_name=config['aws_region'])
        
        project_prefix = "stock-pipeline"
        refresh_token_param = f"/{project_prefix}/fyers/refresh_token"
        
        response = ssm_client.get_parameter(Name=refresh_token_param, WithDecryption=True)
        refresh_token = response['Parameter']['Value']
        
        print("✅ Found refresh token in SSM")
        
    except Exception as e:
        print(f"⚠️ Could not get refresh token from SSM: {e}")
        refresh_token = input("Enter your refresh token manually: ").strip()
    
    if not refresh_token or refresh_token == 'CHANGE_ME':
        print("❌ No valid refresh token available")
        return
    
    # Generate app hash
    app_id_hash = hashlib.sha256(f"{config['client_id']}:{config['app_secret']}".encode()).hexdigest()
    
    # Refresh token request
    refresh_payload = {
        'grant_type': 'refresh_token',
        'appIdHash': app_id_hash,
        'refresh_token': refresh_token
    }
    
    refresh_url = f"{FYERS_BASE_URL}/api/v3/validate-refresh-token"
    headers = {'Content-Type': 'application/json'}
    
    print(f"📡 Refreshing token...")
    
    try:
        response = requests.post(refresh_url, json=refresh_payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('s') == 'ok' and 'access_token' in data:
                new_access_token = data['access_token']
                print("✅ Token refreshed successfully!")
                print(f"🔐 New Access Token: {new_access_token[:20]}...{new_access_token[-10:]}")
                
                # Update SSM with new access token
                try:
                    project_prefix = "stock-pipeline"
                    access_token_param = f"/{project_prefix}/fyers/access_token"
                    
                    ssm_client.put_parameter(
                        Name=access_token_param,
                        Value=new_access_token,
                        Type='SecureString',
                        Overwrite=True,
                        Description=f"Fyers access token - refreshed {datetime.now().isoformat()}"
                    )
                    
                    print("✅ SSM parameter updated with new access token")
                    
                    # Test the new token
                    if test_token_validity(config['client_id'], new_access_token):
                        print("🎉 Token refresh and validation successful!")
                    
                except Exception as e:
                    print(f"⚠️ Could not update SSM: {e}")
                    print(f"💾 New access token: {new_access_token}")
                    
            else:
                print(f"❌ Refresh failed: {data.get('message', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")

def main():
    parser = argparse.ArgumentParser(description='Manual Fyers Token Generator')
    parser.add_argument('--step', type=int, choices=[1, 2, 3], help='Step to execute (1: auth URL, 2: get tokens, 3: update SSM)')
    parser.add_argument('--auth-code', help='Authorization code from Fyers redirect')
    parser.add_argument('--access-token', help='Access token to store in SSM')
    parser.add_argument('--refresh-token', help='Refresh token to store in SSM')
    parser.add_argument('--refresh', action='store_true', help='Refresh existing token instead of full auth flow')
    
    args = parser.parse_args()
    
    print("🔐 Manual Fyers Token Generator")
    print("=" * 50)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load configuration
    config = load_config()
    
    if args.refresh:
        refresh_existing_token(config)
        return
    
    if not args.step:
        print("❓ No step specified. Here's what you can do:")
        print()
        print("🚀 Full token generation process:")
        print("   1. Generate auth URL:     python manual_token_generator.py --step 1")
        print("   2. Get tokens:           python manual_token_generator.py --step 2 --auth-code CODE")
        print("   3. Update SSM:           python manual_token_generator.py --step 3 --access-token TOKEN --refresh-token TOKEN")
        print()
        print("🔄 Quick refresh:")
        print("   Refresh existing:        python manual_token_generator.py --refresh")
        print()
        return
    
    if args.step == 1:
        step1_generate_auth_url(config)
    
    elif args.step == 2:
        if not args.auth_code:
            print("❌ Error: --auth-code is required for step 2")
            return
        step2_get_tokens(config, args.auth_code)
    
    elif args.step == 3:
        if not args.access_token or not args.refresh_token:
            print("❌ Error: --access-token and --refresh-token are required for step 3")
            return
        step3_update_ssm(config, args.access_token, args.refresh_token)

if __name__ == "__main__":
    main()
