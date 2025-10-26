#!/usr/bin/env python3
"""
MVP Demo Setup Script
This script prepares everything for your Saturday demo
"""

import subprocess
import json
import sys
import time
from datetime import datetime

def run_command(command, description=""):
    """Run a command and return the result"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Success")
            return result.stdout.strip()
        else:
            print(f"❌ {description} - Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ {description} - Exception: {e}")
        return None

def get_terraform_output(output_name):
    """Get a specific Terraform output"""
    command = f'cd "../infra" && terraform output -raw {output_name}'
    return run_command(command, f"Getting {output_name}")

def main():
    print("🎬 MVP Demo Setup for Saturday")
    print("=" * 50)
    
    # Step 1: Get project information
    print("\n📋 Step 1: Getting project information...")
    bucket_name = get_terraform_output("s3_bucket_name")
    lambda_name = get_terraform_output("lambda_function_name") 
    
    if not bucket_name or not lambda_name:
        print("❌ Could not get project info. Make sure Terraform has been applied.")
        return
    
    print(f"   S3 Bucket: {bucket_name}")
    print(f"   Lambda Function: {lambda_name}")
    
    # Step 2: Enable demo mode
    print("\n🎭 Step 2: Enabling demo mode...")
    demo_command = f'aws ssm put-parameter --name "/stock-pipeline/demo_mode" --value "true" --type "String" --overwrite'
    result = run_command(demo_command, "Setting demo mode to true")
    
    if result is not None:
        print("✅ Demo mode enabled! Lambda will now bypass trading hours.")
    
    # Step 3: Test Lambda function
    print("\n🚀 Step 3: Testing Lambda function...")
    invoke_command = f'aws lambda invoke --function-name {lambda_name} response.json --log-type Tail'
    result = run_command(invoke_command, "Invoking Lambda function")
    
    if result:
        # Parse response
        try:
            with open('response.json', 'r') as f:
                response = json.load(f)
            print(f"   Lambda Response: {response}")
            
            # Check if successful
            if response.get('statusCode') == 200:
                print("✅ Lambda executed successfully!")
            else:
                print(f"⚠️  Lambda returned status: {response.get('statusCode')}")
                
        except Exception as e:
            print(f"❌ Could not parse Lambda response: {e}")
    
    # Step 4: Check S3 for data
    print("\n📦 Step 4: Checking S3 for generated data...")
    list_command = f'aws s3 ls s3://{bucket_name}/ohlcv/ --recursive'
    result = run_command(list_command, "Listing S3 objects")
    
    if result and result.strip():
        print("✅ Data files found in S3:")
        files = result.strip().split('\n')
        for file in files[-5:]:  # Show last 5 files
            print(f"   📄 {file}")
        if len(files) > 5:
            print(f"   ... and {len(files) - 5} more files")
    else:
        print("⚠️  No data files found in S3 yet. Lambda may still be running.")
    
    # Step 5: Generate demo URLs
    print("\n🔗 Step 5: Demo URLs and Commands...")
    region = "ap-south-1"
    
    s3_url = f"https://s3.console.aws.amazon.com/s3/buckets/{bucket_name}?region={region}"
    logs_url = f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups/log-group/$252Faws$252Flambda$252F{lambda_name}"
    
    print(f"📊 S3 Console: {s3_url}")
    print(f"📋 CloudWatch Logs: {logs_url}")
    
    # Step 6: Demo script
    print(f"\n🎯 Demo Script for Saturday:")
    print("=" * 50)
    print("1. Show the S3 bucket with OHLCV data files")
    print("2. Navigate to CloudWatch logs to show successful execution")
    print("3. Run the dashboard: python scripts/dashboard.py")
    print("4. Open: http://localhost:5000")
    print("5. Show real-time stock data in the web interface")
    print("\n💡 Key points to mention:")
    print("   • Fully serverless and free tier compliant")
    print("   • Runs only during trading hours (with demo mode override)")
    print("   • Auto-refreshes Fyers API tokens")
    print("   • Stores data in Parquet format for analytics")
    print("   • Includes monitoring and alerts")
    
    # Step 7: Cleanup instructions
    print(f"\n🧹 After Demo - Cleanup:")
    print('aws ssm put-parameter --name "/stock-pipeline/demo_mode" --value "false" --overwrite')
    
    print(f"\n🎉 Demo setup complete! Your MVP is ready for Saturday.")

if __name__ == "__main__":
    main()
