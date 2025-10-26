#!/usr/bin/env python3
"""
Environment Setup Helper
Creates and configures your .env file for the Stock Price Feed Parser
"""

import os
import shutil
import subprocess
import json
from typing import Dict, Optional

def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

def print_success(text: str):
    print(f"✅ {text}")

def print_warning(text: str):
    print(f"⚠️  {text}")

def print_error(text: str):
    print(f"❌ {text}")

def get_aws_info() -> Dict[str, str]:
    """Get AWS account and region information"""
    try:
        # Get account ID
        result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                              capture_output=True, text=True, check=True)
        identity = json.loads(result.stdout)
        account_id = identity.get('Account', '')
        
        # Get current region
        result = subprocess.run(['aws', 'configure', 'get', 'region'], 
                              capture_output=True, text=True)
        region = result.stdout.strip() or 'ap-south-1'
        
        return {
            'account_id': account_id,
            'region': region
        }
    except Exception as e:
        print_warning(f"Could not get AWS info: {e}")
        return {'account_id': '', 'region': 'ap-south-1'}

def create_env_file() -> bool:
    """Create .env file from template"""
    template_file = '.env.example'
    env_file = '.env'
    
    if not os.path.exists(template_file):
        print_error(f"Template file {template_file} not found!")
        return False
    
    if os.path.exists(env_file):
        response = input(f"\n{env_file} already exists. Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print("Keeping existing .env file.")
            return True
    
    # Copy template to .env
    shutil.copy2(template_file, env_file)
    print_success(f"Created {env_file} from template")
    return True

def update_env_file(config: Dict[str, str]) -> bool:
    """Update .env file with user configuration"""
    env_file = '.env'
    
    if not os.path.exists(env_file):
        print_error(f"{env_file} not found!")
        return False
    
    # Read current content
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Update values
    replacements = {
        'NOTIFICATION_EMAIL=your-email@example.com': f'NOTIFICATION_EMAIL={config["email"]}',
        'AWS_DEFAULT_REGION=ap-south-1': f'AWS_DEFAULT_REGION={config["region"]}',
    'PROJECT_NAME=stock-pipeline': f'PROJECT_NAME={config["project"]}',
        'ENVIRONMENT=dev': f'ENVIRONMENT={config["environment"]}',
        'MONTHLY_BUDGET_LIMIT=5': f'MONTHLY_BUDGET_LIMIT={config["budget"]}',
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Write updated content
    with open(env_file, 'w') as f:
        f.write(content)
    
    print_success("Updated .env file with your configuration")
    return True

def get_user_config() -> Dict[str, str]:
    """Get configuration from user input"""
    print_header("Environment Configuration")
    
    config = {}
    
    # Email address
    while True:
        email = input("Enter your email address for notifications: ").strip()
        if '@' in email and '.' in email:
            config['email'] = email
            break
        else:
            print_error("Invalid email format. Please try again.")
    
    # AWS region
    aws_info = get_aws_info()
    default_region = aws_info['region']
    region = input(f"Enter AWS region [{default_region}]: ").strip()
    config['region'] = region if region else default_region
    
    # Project name
    project = input("Enter project name [stock-pipeline]: ").strip()
    config['project'] = project if project else "stock-pipeline"
    
    # Environment
    environment = input("Enter environment [dev]: ").strip()
    config['environment'] = environment if environment else "dev"
    
    # Budget limit
    budget = input("Enter monthly budget limit in USD [5]: ").strip()
    config['budget'] = budget if budget else "5"
    
    return config

def update_env_after_deployment():
    """Update .env file with AWS resource names after deployment"""
    print_header("Post-Deployment Environment Update")
    
    env_file = '.env'
    if not os.path.exists(env_file):
        print_error(f"{env_file} not found!")
        return False
    
    print("After successful deployment, you need to update your .env file with the actual AWS resource names.")
    print("You can find these in the deployment output or AWS Console.")
    print()
    
    # Get resource names from user
    resources = {}
    
    bucket_name = input("Enter S3 bucket name (from deployment output): ").strip()
    if bucket_name:
        resources['S3_BUCKET_NAME'] = bucket_name
    
    sns_topic = input("Enter SNS topic ARN (from deployment output): ").strip()
    if sns_topic:
        resources['SNS_TOPIC_ARN'] = sns_topic
    
    secret_name = input("Enter Fyers secret name (from deployment output): ").strip()
    if secret_name:
        resources['FYERS_SECRET_NAME'] = secret_name
    
    lambda_name = input("Enter Lambda function name (from deployment output): ").strip()
    if lambda_name:
        resources['LAMBDA_FUNCTION_NAME'] = lambda_name
    
    if not resources:
        print("No resources to update.")
        return True
    
    # Update .env file
    with open(env_file, 'r') as f:
        content = f.read()
    
    for key, value in resources.items():
        # Replace empty values
        old_line = f"{key}="
        new_line = f"{key}={value}"
        content = content.replace(old_line, new_line)
    
    with open(env_file, 'w') as f:
        f.write(content)
    
    print_success("Updated .env file with AWS resource names")
    return True

def validate_env_file() -> bool:
    """Validate .env file configuration"""
    print_header("Validating Environment Configuration")
    
    env_file = '.env'
    if not os.path.exists(env_file):
        print_error(f"{env_file} not found!")
        return False
    
    # Check required variables
    required_vars = [
        'NOTIFICATION_EMAIL',
        'AWS_DEFAULT_REGION',
        'PROJECT_NAME',
        'ENVIRONMENT'
    ]
    
    optional_vars = [
        'S3_BUCKET_NAME',
        'SNS_TOPIC_ARN',
        'FYERS_SECRET_NAME',
        'LAMBDA_FUNCTION_NAME'
    ]
    
    missing_required = []
    empty_optional = []
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    for var in required_vars:
        if f"{var}=" not in content or f"{var}=your-" in content or f"{var}= " in content:
            missing_required.append(var)
        else:
            print_success(f"{var} is configured")
    
    for var in optional_vars:
        if f"{var}=" in content:
            # Check if it has a value
            for line in content.split('\n'):
                if line.startswith(f"{var}=") and not line.strip().endswith('='):
                    print_success(f"{var} is configured")
                    break
            else:
                empty_optional.append(var)
    
    if missing_required:
        print_error(f"Missing required variables: {', '.join(missing_required)}")
        return False
    
    if empty_optional:
        print_warning(f"Empty optional variables (fill after deployment): {', '.join(empty_optional)}")
    
    print_success("Environment configuration is valid!")
    return True

def show_next_steps():
    """Show next steps after environment setup"""
    print_header("Next Steps")
    
    print("🚀 Your environment is configured! Here's what to do next:")
    print()
    print("1. Deploy the infrastructure:")
    print("   cd deployment")
    print("   ./deploy-mvp.sh  # Linux/Mac")
    print("   # OR")
    print("   .\\deploy-mvp.ps1 -NotificationEmail \"$(grep NOTIFICATION_EMAIL .env | cut -d'=' -f2)\"  # Windows")
    print()
    print("2. After deployment, update .env with resource names:")
    print("   python scripts/env_setup.py --post-deployment")
    print()
    print("3. Configure Fyers API credentials in AWS Secrets Manager")
    print()
    print("4. Test your setup:")
    print("   python scripts/pre_deployment_check.py")
    print()
    print("5. Start analyzing data:")
    print("   python analysis/mvp_analyzer.py")

def main():
    """Main setup workflow"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Environment setup helper')
    parser.add_argument('--post-deployment', action='store_true', 
                       help='Update .env file after deployment')
    parser.add_argument('--validate', action='store_true', 
                       help='Validate existing .env file')
    args = parser.parse_args()
    
    print("🔧 Stock Price Feed Parser - Environment Setup")
    print("=" * 50)
    
    if args.post_deployment:
        update_env_after_deployment()
        return
    
    if args.validate:
        validate_env_file()
        return
    
    # Main setup flow
    print("\nThis tool will help you create and configure your .env file.")
    print("The .env file contains all configuration settings for your pipeline.")
    
    # Create .env file from template
    if not create_env_file():
        return
    
    # Get user configuration
    config = get_user_config()
    
    # Update .env file
    if not update_env_file(config):
        return
    
    # Validate configuration
    if not validate_env_file():
        return
    
    print_success("Environment setup complete!")
    show_next_steps()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print(f"\n\nSetup failed: {e}")
        exit(1)
