#!/usr/bin/env python3
"""
OpenClaw + ClawWork Integration Example
Demonstrates browser automation with economic tracking
"""

import httpx
import time
from typing import Dict

# ClawWork API Configuration
API_BASE_URL = "https://clawwork-cloud-api.onrender.com"

class ClawWorkClient:
    """Client for ClawWork economic tracking API"""
    
    def __init__(self, api_url: str = API_BASE_URL):
        self.api_url = api_url
        self.client = httpx.Client()
    
    def get_status(self) -> Dict:
        """Get current economic status"""
        response = self.client.get(f"{self.api_url}/status")
        return response.json()
    
    def start_task(self, task_id: str, task_type: str, estimated_cost: float) -> Dict:
        """Track task start and deduct estimated cost"""
        response = self.client.post(
            f"{self.api_url}/task/start",
            json={
                "task_id": task_id,
                "task_type": task_type,
                "estimated_cost": estimated_cost
            }
        )
        return response.json()
    
    def complete_task(self, task_id: str, success: bool, actual_cost: float, revenue: float = 0.0) -> Dict:
        """Mark task as complete and record revenue"""
        response = self.client.post(
            f"{self.api_url}/task/complete",
            json={
                "task_id": task_id,
                "success": success,
                "actual_cost": actual_cost,
                "actual_revenue": revenue
            }
        )
        return response.json()

def simulate_fiverr_gig_workflow():
    """Simulate automated Fiverr market research gig workflow"""
    tracker = ClawWorkClient()
    
    # Check initial status
    print("\n=== Initial Economic Status ===")
    status = tracker.get_status()
    print(f"Balance: ${status['balance']}")
    print(f"Status: {status['status']}")
    
    # Simulate browser automation task: Market Research
    task_id = "fiverr_market_research_001"
    print(f"\n=== Starting Task: {task_id} ===")
    
    # Start task (deduct estimated cost for browser automation)
    result = tracker.start_task(
        task_id=task_id,
        task_type="fiverr_market_research",
        estimated_cost=0.50  # Cost of automation resources
    )
    print(f"Task started. Current balance: ${result['current_balance']}")
    
    # Simulate work being done
    print("\n[Browser Automation Running...]")
    print("- Researching competitor pricing...")
    time.sleep(1)
    print("- Analyzing market trends...")
    time.sleep(1)
    print("- Generating comprehensive report...")
    time.sleep(1)
    print("- Delivering to Fiverr buyer...")
    
    # Complete task successfully (record revenue)
    result = tracker.complete_task(
        task_id=task_id,
        success=True,
        actual_cost=0.50,
        revenue=25.00  # Fiverr gig payment
    )
    
    print("\n=== Task Completed Successfully ===")
    economics = result['economics']
    print(f"Balance: ${economics['balance']}")
    print(f"Total Income: ${economics['total_income']}")
    print(f"Total Costs: ${economics['total_costs']}")
    print(f"Net Profit: ${economics['net_profit']}")
    print(f"Tasks Completed: {economics['tasks_completed']}")
    print(f"Agent Status: {economics['status'].upper()}")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("OpenClaw + ClawWork Integration Demo")
    print("Automated Fiverr Gig Workflow")
    print("="*50)
    
    simulate_fiverr_gig_workflow()
    
    print("\n" + "="*50)
    print("Integration Complete!")
    print("="*50 + "\n")
