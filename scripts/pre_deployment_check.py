#!/usr/bin/env python3
"""
Pre-Deployment Checklist Script
Verifies all prerequisites are met before deploying the MVP
"""

import subprocess
import sys
import os
import json
import re
from typing import Dict, List, Tuple

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== {text} ==={Colors.END}")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def run_command(command: List[str]) -> Tuple[bool, str]:
    """Run a command and return success status and output"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except FileNotFoundError:
        return False, "Command not found"
    except Exception as e:
        return False, str(e)

def check_aws_cli() -> bool:
    """Check if AWS CLI is installed and configured"""
    print_header("Checking AWS CLI")
    
    # Check if AWS CLI is installed
    success, output = run_command(['aws', '--version'])
    if not success:
        print_error("AWS CLI is not installed")
        print(f"   Install from: https://aws.amazon.com/cli/")
        return False
    
    print_success(f"AWS CLI installed: {output}")
    
    # Check if AWS is configured
    success, output = run_command(['aws', 'sts', 'get-caller-identity'])
    if not success:
        print_error("AWS CLI is not configured")
        print(f"   Run: aws configure")
        print(f"   You need: Access Key ID, Secret Access Key, Region")
        return False
    
    try:
        identity = json.loads(output)
        account_id = identity.get('Account', 'Unknown')
        user_arn = identity.get('Arn', 'Unknown')
        print_success(f"AWS configured - Account: {account_id}")
        print(f"   User: {user_arn}")
        return True
    except json.JSONDecodeError:
        print_error("Could not parse AWS identity")
        return False

def check_terraform() -> bool:
    """Check if Terraform is installed"""
    print_header("Checking Terraform")
    
    success, output = run_command(['terraform', 'version'])
    if not success:
        print_error("Terraform is not installed")
        print(f"   Install from: https://terraform.io/downloads")
        return False
    
    # Extract version from output
    version_match = re.search(r'Terraform v(\d+\.\d+\.\d+)', output)
    if version_match:
        version = version_match.group(1)
        print_success(f"Terraform installed: v{version}")
        
        # Check if version is recent enough
        major, minor, patch = map(int, version.split('.'))
        if major >= 1 and minor >= 0:
            return True
        else:
            print_warning(f"Terraform version {version} is old. Recommend v1.0 or newer")
            return True
    else:
        print_success("Terraform installed")
        return True

def check_python() -> bool:
    """Check if Python is installed"""
    print_header("Checking Python")
    
    success, output = run_command(['python', '--version'])
    if not success:
        # Try python3
        success, output = run_command(['python3', '--version'])
        if not success:
            print_error("Python is not installed")
            print(f"   Install from: https://python.org/downloads")
            return False
    
    # Extract version
    version_match = re.search(r'Python (\d+\.\d+\.\d+)', output)
    if version_match:
        version = version_match.group(1)
        major, minor = map(int, version.split('.')[:2])
        
        if major >= 3 and minor >= 8:
            print_success(f"Python installed: {version}")
            return True
        else:
            print_warning(f"Python {version} detected. Recommend Python 3.8+")
            return True
    else:
        print_success("Python installed")
        return True

def check_git() -> bool:
    """Check if Git is installed"""
    print_header("Checking Git")
    
    success, output = run_command(['git', '--version'])
    if not success:
        print_warning("Git is not installed (optional but recommended)")
        print(f"   Install from: https://git-scm.com/downloads")
        return True  # Git is optional
    
    print_success(f"Git installed: {output}")
    return True

def check_email_format(email: str) -> bool:
    """Check if email format is valid"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_deployment_info() -> Dict[str, str]:
    """Get deployment configuration from user"""
    print_header("Deployment Configuration")
    
    config = {}
    
    # Get email address
    while True:
        email = input("Enter your email address for notifications: ").strip()
        if check_email_format(email):
            config['email'] = email
            print_success(f"Email address: {email}")
            break
        else:
            print_error("Invalid email format. Please try again.")
    
    # Get AWS region
    region = input("Enter AWS region [ap-south-1]: ").strip()
    if not region:
        region = "ap-south-1"
    config['region'] = region
    print_success(f"AWS Region: {region}")
    
    # Get project name
    project = input("Enter project name [stock-pipeline]: ").strip()
    if not project:
        project = "stock-pipeline"
    config['project'] = project
    print_success(f"Project name: {project}")
    
    return config

def check_aws_region(region: str) -> bool:
    """Verify the AWS region is valid"""
    print_header("Validating AWS Region")
    
    success, output = run_command(['aws', 'ec2', 'describe-regions', '--region', region])
    if not success:
        print_error(f"Invalid AWS region: {region}")
        print("   Common regions: ap-south-1, us-east-1, us-west-2, eu-west-1")
        return False
    
    print_success(f"AWS region {region} is valid")
    return True

def check_file_structure() -> bool:
    """Check if required files exist"""
    print_header("Checking File Structure")
    
    required_files = [
    'infra/main-mvp.tf',
        'deployment/deploy-mvp.ps1',
        'deployment/deploy-mvp.sh',
        'ingestion/lambda_ingestion.py',
        'analysis/mvp_analyzer.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print_success(f"Found: {file_path}")
        else:
            print_error(f"Missing: {file_path}")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def estimate_costs() -> None:
    """Show cost estimates"""
    print_header("Cost Estimates")
    
    print("💰 Expected Monthly Costs (MVP):")
    print("   • S3 Storage: FREE (5GB limit)")
    print("   • Lambda: FREE (1M requests limit)")
    print("   • SNS Notifications: FREE (1K notifications limit)")
    print("   • CloudWatch Logs: FREE (5GB limit)")
    print("   • SSM Parameter Store: FREE (standard parameters)")
    print("   • EventBridge: FREE")
    print("   • Cost Explorer: FREE")
    print()
    print("💡 Total Estimated Cost: $0.00 - $1.00/month (FREE TIER)")
    print()
    print("⚠️  Cost Control Measures:")
    print("   • Budget alert at $2.50 (50% of $5 budget)")
    print("   • Budget alert at $4.00 (80% of $5 budget)")
    print("   • S3 lifecycle policies for cost optimization")
    print("   • Lambda timeout set to 5 minutes max")
    print("   • Only 10 stocks to minimize API calls")

def show_next_steps(config: Dict[str, str]) -> None:
    """Show next steps after successful verification"""
    print_header("Next Steps")
    
    print("🚀 You're ready to deploy! Follow these steps:")
    print()
    print("1. Navigate to the deployment directory:")
    if os.name == 'nt':  # Windows
        print("   cd deployment")
        print(f"   .\\deploy-mvp.ps1 -NotificationEmail \"{config['email']}\"")
    else:  # Linux/Mac
        print("   cd deployment")
        print(f"   export NOTIFICATION_EMAIL=\"{config['email']}\"")
        print("   chmod +x deploy-mvp.sh")
        print("   ./deploy-mvp.sh")
    
    print()
    print("2. After deployment, configure your Fyers API credentials:")
    print("   • Use AWS CLI to store credentials in SSM Parameter Store:")
    print("     aws ssm put-parameter --name '/project-name/fyers/client_id' --value 'YOUR_CLIENT_ID' --type 'SecureString' --overwrite")
    print("     aws ssm put-parameter --name '/project-name/fyers/app_secret' --value 'YOUR_APP_SECRET' --type 'SecureString' --overwrite")
    print("     aws ssm put-parameter --name '/project-name/fyers/refresh_token' --value 'YOUR_REFRESH_TOKEN' --type 'SecureString' --overwrite")
    print("   • Confirm email subscription for notifications")
    
    print()
    print("3. Monitor your deployment:")
    print("   • Check CloudWatch logs for Lambda execution")
    print("   • Verify data appears in S3 bucket")
    print("   • Run analysis script to view your data")
    
    print()
    print("4. Cost monitoring:")
    print("   • Check AWS Billing Dashboard weekly")
    print("   • Run cost monitoring script: python monitoring/cost_monitor.py")
    print("   • Set up additional billing alerts if needed")

def main():
    """Main verification workflow"""
    print(f"{Colors.BLUE}{Colors.BOLD}")
    print("🔍 AWS MVP Pre-Deployment Checklist")
    print("====================================")
    print("This script verifies you have everything needed to deploy the stock price feed parser MVP.")
    print(f"{Colors.END}")
    
    checks_passed = 0
    total_checks = 6
    
    # Run all checks
    if check_aws_cli():
        checks_passed += 1
    
    if check_terraform():
        checks_passed += 1
    
    if check_python():
        checks_passed += 1
    
    if check_git():
        checks_passed += 1
    
    if check_file_structure():
        checks_passed += 1
    
    # Get deployment configuration
    config = get_deployment_info()
    
    # Validate region
    if check_aws_region(config['region']):
        checks_passed += 1
    
    # Show cost estimates
    estimate_costs()
    
    # Summary
    print_header("Verification Summary")
    
    if checks_passed == total_checks:
        print_success(f"All checks passed! ({checks_passed}/{total_checks})")
        print("✨ You're ready to deploy the MVP!")
        
        # Ask for confirmation
        print("\nDo you want to see the deployment commands? (y/n): ", end="")
        if input().lower().startswith('y'):
            show_next_steps(config)
    
    else:
        print_error(f"Some checks failed ({checks_passed}/{total_checks})")
        print("Please fix the issues above before deploying.")
        
        if checks_passed >= 4:
            print_warning("You have most requirements met. Consider proceeding with caution.")
    
    print(f"\n{Colors.BLUE}💡 Need help? Check the BEGINNER_GUIDE.md for detailed instructions.{Colors.END}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Verification cancelled by user.{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Verification failed: {e}{Colors.END}")
        sys.exit(1)
