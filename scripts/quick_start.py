#!/usr/bin/env python3
"""
Quick Start Guide - Interactive Setup Wizard
Walks through the entire deployment process step by step
"""

import os
import sys
import subprocess
import time
import json
from typing import Dict, List

class QuickStartWizard:
    def __init__(self):
        self.config = {}
        self.step = 1
        
    def print_banner(self):
        print("""
╔══════════════════════════════════════════════════════════════╗
║                 🚀 Stock Price Feed Parser                   ║
║                   Quick Start Wizard                         ║
║                                                              ║
║  This wizard will guide you through deploying a complete    ║
║  stock data pipeline on AWS Free Tier (costs ~$0.40/month) ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
    def print_step(self, title: str, description: str = ""):
        print(f"\n{'='*60}")
        print(f"STEP {self.step}: {title}")
        print(f"{'='*60}")
        if description:
            print(f"{description}\n")
        self.step += 1
        
    def wait_for_user(self, message: str = "Press Enter to continue..."):
        input(f"\n{message}")
        
    def run_command(self, command: List[str], description: str = "") -> bool:
        """Run a command with user feedback"""
        if description:
            print(f"Running: {description}")
        
        print(f"Command: {' '.join(command)}")
        
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            print("✅ Success!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed: {e}")
            print(f"Error output: {e.stderr}")
            return False
        except FileNotFoundError:
            print(f"❌ Command not found: {command[0]}")
            return False
            
    def step_welcome(self):
        self.print_step("Welcome", 
                       "Let's set up your stock data pipeline on AWS!")
        
        print("What you'll get:")
        print("• 📊 Automated stock data collection every 15 minutes")
        print("• 🏗️  Complete AWS infrastructure (S3, Lambda, SNS)")
        print("• 📧 Email notifications for system status")
        print("• 📈 Local data analysis and visualization tools")
        print("• 💰 Optimized for AWS Free Tier (~$0.40/month)")
        
        print("\nWhat you need:")
        print("• ✅ AWS account (free)")
        print("• ✅ Fyers API credentials")
        print("• ✅ Email address for notifications")
        print("• ⏱️  About 20-30 minutes")
        
        self.wait_for_user("Ready to start? Press Enter to continue...")
        
    def step_prerequisites(self):
        self.print_step("Check Prerequisites", 
                       "Let's verify you have all required tools installed.")
        
        print("Running pre-deployment check...")
        
        # Run the pre-deployment check
        if os.name == 'nt':  # Windows
            script_path = "scripts\\pre_deployment_check.ps1"
            if os.path.exists(script_path):
                success = self.run_command(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path, "-SkipInteractive"],
                    "Checking prerequisites"
                )
            else:
                print("⚠️  Pre-deployment check script not found")
                success = False
        else:  # Linux/Mac
            script_path = "scripts/pre_deployment_check.py"
            if os.path.exists(script_path):
                success = self.run_command(["python3", script_path], "Checking prerequisites")
            else:
                print("⚠️  Pre-deployment check script not found")
                success = False
        
        if not success:
            print("\n❌ Prerequisites check failed!")
            print("Please install missing tools and run this wizard again.")
            print("\nFor detailed instructions, see: BEGINNER_GUIDE.md")
            sys.exit(1)
        
        print("\n✅ All prerequisites met!")
        self.wait_for_user()
        
    def step_aws_setup(self):
        self.print_step("AWS Account Setup", 
                       "Let's verify your AWS account is ready.")
        
        print("Checking AWS configuration...")
        
        # Test AWS CLI
        try:
            result = subprocess.run(["aws", "sts", "get-caller-identity"], 
                                  capture_output=True, text=True, check=True)
            identity = json.loads(result.stdout)
            account_id = identity.get('Account', 'Unknown')
            
            print(f"✅ AWS Account: {account_id}")
            print(f"✅ User: {identity.get('Arn', 'Unknown')}")
            
        except Exception as e:
            print(f"❌ AWS configuration issue: {e}")
            print("\nPlease run: aws configure")
            print("You need your AWS Access Key ID and Secret Access Key")
            print("\nFor help, see: BEGINNER_GUIDE.md section 4")
            sys.exit(1)
        
        # Warn about costs
        print("\n💰 COST INFORMATION:")
        print("• This deployment uses AWS Free Tier services")
        print("• Expected cost: $0.40 - $2.00 per month")
        print("• We'll set up budget alerts to monitor costs")
        print("• You can delete everything anytime to stop costs")
        
        response = input("\nDo you want to continue? (y/n): ").strip().lower()
        if response != 'y':
            print("Deployment cancelled.")
            sys.exit(0)
            
    def step_configuration(self):
        self.print_step("Configuration", 
                       "Let's configure your deployment settings.")
        
        # Get email address
        while True:
            email = input("Enter your email address for notifications: ").strip()
            if '@' in email and '.' in email:
                self.config['email'] = email
                break
            else:
                print("❌ Invalid email format. Please try again.")
        
        # Get AWS region
        region = input("Enter AWS region [ap-south-1]: ").strip()
        if not region:
            region = "ap-south-1"
        self.config['region'] = region
        
        # Get project name
        project = input("Enter project name [stock-pipeline]: ").strip()
        if not project:
            project = "stock-pipeline"
        self.config['project'] = project
        
        print(f"\n✅ Configuration saved:")
        print(f"   Email: {self.config['email']}")
        print(f"   Region: {self.config['region']}")
        print(f"   Project: {self.config['project']}")
        
    def step_deployment(self):
        self.print_step("Deploy Infrastructure", 
                       "Now let's deploy your stock data pipeline to AWS.")
        
        print("This will create the following AWS resources:")
        print("• S3 bucket for data storage")
        print("• Lambda function for data collection")
        print("• SNS topic for email notifications")
        print("• SSM Parameter Store for API credentials (FREE)")
        print("• CloudWatch for logging")
        print("• Cost budget and alerts")
        
        print("\n⏱️  This process takes about 5-15 minutes...")
        
        self.wait_for_user("Ready to deploy? Press Enter to continue...")
        
        # Change to deployment directory
        if not os.path.exists("deployment"):
            print("❌ Deployment directory not found!")
            sys.exit(1)
        
        original_dir = os.getcwd()
        os.chdir("deployment")
        
        try:
            # Run deployment script
            if os.name == 'nt':  # Windows
                success = self.run_command([
                    "powershell", "-ExecutionPolicy", "Bypass", "-File", 
                    "deploy-mvp.ps1", "-NotificationEmail", self.config['email']
                ], "Deploying AWS infrastructure")
            else:  # Linux/Mac
                # Set environment variable
                os.environ['NOTIFICATION_EMAIL'] = self.config['email']
                success = self.run_command(["./deploy-mvp.sh"], "Deploying AWS infrastructure")
            
            if success:
                print("\n🎉 Deployment successful!")
            else:
                print("\n❌ Deployment failed!")
                print("Check the error messages above and try again.")
                sys.exit(1)
                
        finally:
            os.chdir(original_dir)
            
    def step_fyers_setup(self):
        self.print_step("Fyers API Setup", 
                       "Now let's configure your Fyers API credentials.")
        
        print("To get Fyers API credentials:")
        print("1. 🌐 Go to fyers.in and create/login to your account")
        print("2. 🔧 Navigate to API section (usually under Developer/Tools)")
        print("3. 📝 Create a new API app:")
        print("   - App Name: Stock Price Tracker")
        print("   - App Type: Web App")
        print("   - Redirect URL: https://trade.fyers.in/api-login")
        print("4. 📋 Copy your credentials:")
        print("   - Client ID (looks like: ABC123-100)")
        print("   - App Secret (looks like: xyz123...)")
        print("   - Refresh Token (get after login flow)")
        
        print("\n⚠️  IMPORTANT: Keep these credentials secure!")
        
        self.wait_for_user("Have you obtained your Fyers API credentials? Press Enter when ready...")
        
        # Get credentials from user
        print("\nEnter your Fyers API credentials:")
        client_id = input("Client ID: ").strip()
        app_secret = input("App Secret: ").strip()
        refresh_token = input("Refresh Token: ").strip()
        
        if not all([client_id, app_secret, refresh_token]):
            print("❌ Client ID, App Secret, and Refresh Token are all required!")
            print("You can update them later in AWS SSM Parameter Store.")
        else:
            # Update AWS SSM Parameter Store
            project_name = self.config.get('project', 'stock-pipeline')
            
            # Store client_id
            success1 = self.run_command([
                "aws", "ssm", "put-parameter",
                "--name", f"/{project_name}/fyers/client_id",
                "--value", client_id,
                "--type", "SecureString",
                "--overwrite"
            ], "Storing Fyers Client ID in SSM Parameter Store")
            
            # Store app_secret
            success2 = self.run_command([
                "aws", "ssm", "put-parameter",
                "--name", f"/{project_name}/fyers/app_secret",
                "--value", app_secret,
                "--type", "SecureString",
                "--overwrite"
            ], "Storing Fyers App Secret in SSM Parameter Store")
            
            # Store refresh_token
            success3 = self.run_command([
                "aws", "ssm", "put-parameter", 
                "--name", f"/{project_name}/fyers/refresh_token",
                "--value", refresh_token,
                "--type", "SecureString",
                "--overwrite"
            ], "Storing Fyers Refresh Token in SSM Parameter Store")
            
            success = success1 and success2 and success3
            
            if success:
                print("✅ Fyers API credentials configured!")
            else:
                print("❌ Failed to update credentials. You can do this manually later.")
                
    def step_testing(self):
        self.print_step("Test Your Pipeline", 
                       "Let's test that everything is working correctly.")
        
        print("Testing Lambda function...")
        
        # Test Lambda function
        success = self.run_command([
            "aws", "lambda", "invoke",
            "--function-name", f"{self.config['project']}-ingestion",
            "--payload", "{}",
            "test_output.json"
        ], "Testing Lambda function")
        
        if success:
            print("✅ Lambda function test successful!")
            
            # Check if output file exists
            if os.path.exists("test_output.json"):
                try:
                    with open("test_output.json", 'r') as f:
                        result = json.load(f)
                    print(f"Function response: {result}")
                    os.remove("test_output.json")
                except:
                    pass
        else:
            print("⚠️  Lambda test failed, but this might be due to API credentials.")
            print("Check CloudWatch logs for details.")
        
        print("\n📧 Check your email for notifications!")
        print("You should receive an email about the test execution.")
        
    def step_monitoring(self):
        self.print_step("Set Up Monitoring", 
                       "Let's set up monitoring for your pipeline.")
        
        print("Your pipeline includes built-in monitoring:")
        print("• 📧 Email notifications for success/failure")
        print("• 📊 CloudWatch logs for detailed execution info")
        print("• 💰 Cost budget alerts")
        print("• 📈 S3 storage monitoring")
        
        print("\nImportant URLs (bookmark these!):")
        region = self.config['region']
        print(f"• AWS Console: https://console.aws.amazon.com")
        print(f"• CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups")
        print(f"• S3 Console: https://s3.console.aws.amazon.com/s3/")
        print(f"• Billing Dashboard: https://console.aws.amazon.com/billing/")
        
        print("\n💡 Monitoring tips:")
        print("• Check email notifications daily")
        print("• Review AWS billing weekly")
        print("• Monitor CloudWatch logs if issues occur")
        print("• Run cost monitoring script monthly")
        
    def step_data_analysis(self):
        self.print_step("Data Analysis Setup", 
                       "Let's set up local data analysis tools.")
        
        print("Installing Python packages for data analysis...")
        
        packages = ["pandas", "matplotlib", "seaborn", "boto3"]
        for package in packages:
            success = self.run_command(
                ["pip", "install", package],
                f"Installing {package}"
            )
            if not success:
                print(f"⚠️  Failed to install {package}. You can install it manually later.")
        
        print("\n📊 To analyze your data:")
        print("1. Wait for data collection (15-30 minutes)")
        print("2. Run the analysis script:")
        print("   cd analysis")
        print(f"   set S3_BUCKET_NAME=your-bucket-name  # Windows")
        print(f"   export S3_BUCKET_NAME=your-bucket-name  # Linux/Mac")
        print("   python mvp_analyzer.py")
        
        print("\n📈 The analysis will generate:")
        print("• Price trend charts")
        print("• Volume analysis")
        print("• Stock correlation heatmaps")
        print("• Daily statistics reports")
        
    def step_completion(self):
        self.print_step("🎉 Setup Complete!", 
                       "Congratulations! Your stock data pipeline is running!")
        
        print("What's happening now:")
        print("• 🔄 Lambda function runs every 15 minutes")
        print("• 📊 Collecting data for 10 top NSE stocks")
        print("• 💾 Storing data in S3 bucket")
        print("• 📧 Sending you email notifications")
        
        print("\nNext steps:")
        print("1. ⏰ Wait 15-30 minutes for initial data collection")
        print("2. 📧 Check your email for notifications")
        print("3. 📊 Run analysis script to view your data")
        print("4. 💰 Monitor costs in AWS Billing Dashboard")
        
        print("\nImportant commands:")
        print("• Check costs: python monitoring/cost_monitor.py")
        print("• Analyze data: python analysis/mvp_analyzer.py")
        print("• View logs: Check CloudWatch in AWS Console")
        
        print(f"\n📋 Your deployment summary:")
        print(f"   Project: {self.config['project']}")
        print(f"   Email: {self.config['email']}")
        print(f"   Region: {self.config['region']}")
        print(f"   Expected cost: $0.40-$2.00/month")
        
        print("\n🚀 To scale up later:")
        print("   Edit infra/main-mvp.tf and uncomment production services")
        print("   (RDS, ECS, Glue, Athena for advanced features)")
        
        print("\n📚 Need help?")
        print("   • Read BEGINNER_GUIDE.md for detailed instructions")
        print("   • Check CloudWatch logs for troubleshooting")
        print("   • Monitor AWS billing dashboard")
        
        print("\n🎊 Enjoy your automated stock data pipeline!")
        
    def run(self):
        """Run the complete wizard"""
        try:
            self.print_banner()
            self.step_welcome()
            self.step_prerequisites()
            self.step_aws_setup()
            self.step_configuration()
            self.step_deployment()
            self.step_fyers_setup()
            self.step_testing()
            self.step_monitoring()
            self.step_data_analysis()
            self.step_completion()
            
        except KeyboardInterrupt:
            print("\n\n❌ Setup cancelled by user.")
            sys.exit(0)
        except Exception as e:
            print(f"\n\n❌ Setup failed: {e}")
            sys.exit(1)

if __name__ == '__main__':
    wizard = QuickStartWizard()
    wizard.run()
