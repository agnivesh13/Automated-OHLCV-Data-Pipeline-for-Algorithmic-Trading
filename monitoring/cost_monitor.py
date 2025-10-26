#!/usr/bin/env python3
"""
MVP Cost Monitoring Script
Tracks AWS costs for the MVP deployment to ensure Free Tier compliance
"""

import boto3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MVPCostMonitor:
    """Monitor AWS costs for MVP deployment"""
    
    def __init__(self):
        self.ce_client = boto3.client('ce')  # Cost Explorer
        self.budgets_client = boto3.client('budgets')
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
    
    def get_current_month_costs(self) -> Dict:
        """Get current month costs by service"""
        try:
            # Calculate date range for current month
            today = datetime.now()
            start_of_month = today.replace(day=1).strftime('%Y-%m-%d')
            end_of_month = (today + timedelta(days=32)).replace(day=1).strftime('%Y-%m-%d')
            
            # Get cost by service
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_of_month,
                    'End': end_of_month
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ],
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [
                            'Amazon Simple Storage Service',
                            'AWS Lambda',
                            'Amazon Simple Notification Service',
                            'AWS Secrets Manager',
                            'Amazon CloudWatch'
                        ]
                    }
                }
            )
            
            costs = {}
            total_cost = 0
            
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    costs[service] = cost
                    total_cost += cost
            
            costs['Total'] = total_cost
            return costs
            
        except Exception as e:
            logger.error(f"Failed to get cost data: {e}")
            return {}
    
    def get_free_tier_usage(self) -> Dict:
        """Get Free Tier usage information"""
        try:
            # Get last 30 days of usage
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            response = self.ce_client.get_usage_forecast(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Metric='USAGE_QUANTITY',
                Granularity='MONTHLY',
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [
                            'Amazon Simple Storage Service',
                            'AWS Lambda'
                        ]
                    }
                }
            )
            
            return response
            
        except Exception as e:
            logger.warning(f"Could not get Free Tier usage data: {e}")
            return {}
    
    def check_budget_status(self, budget_name: str) -> Dict:
        """Check budget status for the MVP"""
        try:
            response = self.budgets_client.describe_budget(
                AccountId=self.account_id,
                BudgetName=budget_name
            )
            
            budget = response['Budget']
            
            # Get budget performance
            performance_response = self.budgets_client.describe_budget_performance(
                AccountId=self.account_id,
                BudgetName=budget_name
            )
            
            return {
                'budget_limit': float(budget['BudgetLimit']['Amount']),
                'budget_unit': budget['BudgetLimit']['Unit'],
                'actual_spend': float(performance_response['BudgetPerformance']['ActualSpend']['Amount']),
                'forecasted_spend': float(performance_response['BudgetPerformance']['ForecastedSpend']['Amount']),
                'budget_type': budget['BudgetType'],
                'time_unit': budget['TimeUnit']
            }
            
        except Exception as e:
            logger.warning(f"Could not get budget status: {e}")
            return {}
    
    def generate_cost_report(self) -> str:
        """Generate a comprehensive cost report"""
        try:
            report = []
            report.append("=== MVP Cost Monitoring Report ===")
            report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
            
            # Current month costs
            costs = self.get_current_month_costs()
            if costs:
                report.append("💰 CURRENT MONTH COSTS:")
                for service, cost in costs.items():
                    if service != 'Total':
                        status = "✅ FREE" if cost == 0 else f"💸 ${cost:.2f}"
                        service_name = service.replace('Amazon ', '').replace('AWS ', '')
                        report.append(f"  • {service_name}: {status}")
                
                total_cost = costs.get('Total', 0)
                report.append(f"  • TOTAL: ${total_cost:.2f}")
                report.append("")
                
                # Free tier status
                if total_cost == 0:
                    report.append("🎉 EXCELLENT! You're completely within Free Tier limits!")
                elif total_cost < 1.0:
                    report.append("✅ GOOD! You're mostly within Free Tier with minimal costs.")
                elif total_cost < 5.0:
                    report.append("⚠️  CAUTION! Costs are increasing but still reasonable for MVP.")
                else:
                    report.append("🚨 WARNING! Costs are higher than expected for MVP.")
                
                report.append("")
            
            # Budget status
            budget_status = self.check_budget_status("stock-pipeline-budget")
            if budget_status:
                report.append("📊 BUDGET STATUS:")
                budget_limit = budget_status['budget_limit']
                actual_spend = budget_status['actual_spend']
                forecasted_spend = budget_status['forecasted_spend']
                
                usage_percent = (actual_spend / budget_limit) * 100
                forecast_percent = (forecasted_spend / budget_limit) * 100
                
                report.append(f"  • Budget Limit: ${budget_limit:.2f}")
                report.append(f"  • Actual Spend: ${actual_spend:.2f} ({usage_percent:.1f}%)")
                report.append(f"  • Forecasted: ${forecasted_spend:.2f} ({forecast_percent:.1f}%)")
                
                if usage_percent < 50:
                    report.append("  • Status: ✅ Well within budget")
                elif usage_percent < 80:
                    report.append("  • Status: ⚠️  Approaching budget limit")
                else:
                    report.append("  • Status: 🚨 Budget limit exceeded!")
                
                report.append("")
            
            # Free Tier recommendations
            report.append("💡 FREE TIER OPTIMIZATION TIPS:")
            report.append("  • S3: Use lifecycle policies to move old data to cheaper storage")
            report.append("  • Lambda: Optimize function duration and memory allocation")
            report.append("  • CloudWatch: Set short log retention periods")
            report.append("  • Secrets Manager: Consider environment variables for non-sensitive config")
            report.append("  • SNS: Use consolidated notifications to reduce message count")
            report.append("")
            
            # Cost control actions
            report.append("🛡️  COST CONTROL ACTIONS:")
            if total_cost == 0:
                report.append("  • Continue monitoring usage patterns")
                report.append("  • Set up billing alerts for any unexpected charges")
            elif total_cost < 2.0:
                report.append("  • Monitor daily for any unusual spikes")
                report.append("  • Review resource utilization weekly")
            else:
                report.append("  • 🚨 IMMEDIATE: Review all running resources")
                report.append("  • 🚨 IMMEDIATE: Check for any unexpected deployments")
                report.append("  • 🚨 IMMEDIATE: Consider scaling down or pausing services")
            
            report.append("")
            report.append("📋 MONITORING CHECKLIST:")
            report.append("  □ Check AWS Free Tier usage dashboard monthly")
            report.append("  □ Review Cost Explorer for unexpected services")
            report.append("  □ Verify no production resources are running")
            report.append("  □ Confirm all expensive services are commented out")
            report.append("  □ Monitor email alerts for budget notifications")
            
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"Failed to generate cost report: {e}")
            return f"Cost report generation failed: {e}"
    
    def get_service_recommendations(self, costs: Dict) -> List[str]:
        """Get specific recommendations based on current costs"""
        recommendations = []
        
        s3_cost = costs.get('Amazon Simple Storage Service', 0)
        lambda_cost = costs.get('AWS Lambda', 0)
        secrets_cost = costs.get('AWS Secrets Manager', 0)
        
        if s3_cost > 1.0:
            recommendations.append("S3 costs are high - check for large files or excessive requests")
        
        if lambda_cost > 0.5:
            recommendations.append("Lambda costs detected - optimize function memory and duration")
        
        if secrets_cost > 1.0:
            recommendations.append("Multiple secrets detected - consolidate if possible")
        
        return recommendations

def main():
    """Main monitoring workflow"""
    try:
        logger.info("Starting MVP cost monitoring")
        
        # Initialize monitor
        monitor = MVPCostMonitor()
        
        # Generate report
        report = monitor.generate_cost_report()
        
        # Print report
        print(report)
        
        # Save report to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"mvp_cost_report_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write(report)
        
        logger.info(f"Cost report saved to: {filename}")
        
    except Exception as e:
        logger.error(f"Cost monitoring failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
