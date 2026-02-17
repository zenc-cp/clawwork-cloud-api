from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Optional
import json
import os

app = FastAPI(title="ClawWork Cloud API", version="1.0.0")

# Economic Tracker
class EconomicTracker:
    def __init__(self):
        self.balance = float(os.getenv("INITIAL_BALANCE", "10.0"))
        self.total_income = 0.0
        self.total_costs = 0.0
        self.tasks_completed = 0
        self.tasks_failed = 0

    def track_cost(self, amount: float):
        self.total_costs += amount
        self.balance -= amount

    def track_income(self, amount: float):
        self.total_income += amount
        self.balance += amount
        self.tasks_completed += 1

    def get_status(self) -> Dict:
        return {
            "balance": round(self.balance, 2),
            "total_income": round(self.total_income, 2),
            "total_costs": round(self.total_costs, 2),
            "net_profit": round(self.total_income - self.total_costs, 2),
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "status": "thriving" if self.balance > 50 else "critical" if self.balance < 10 else "surviving"
        }

tracker = EconomicTracker()

# OpenClaw Browser Task Model
class BrowserTask(BaseModel):
    task_id: str
    task_type: str
    estimated_cost: Optional[float] = None
    expected_revenue: Optional[float] = None

class TaskResult(BaseModel):
    task_id: str
    success: bool
    actual_cost: float
    actual_revenue: float = 0.0

@app.get("/")
def root():
    return {"message": "ClawWork Cloud API", "status": "active", "version": "1.0.0"}

@app.get("/status")
def get_status():
    return tracker.get_status()

@app.post("/task/start")
def start_task(task: BrowserTask):
    if task.estimated_cost:
        tracker.track_cost(task.estimated_cost)
    return {
        "task_id": task.task_id,
        "status": "started",
        "current_balance": round(tracker.balance, 2)
    }

@app.post("/task/complete")
def complete_task(result: TaskResult):
    if result.success:
        tracker.track_income(result.actual_revenue)
    else:
        tracker.tasks_failed += 1
    
    return {
        "task_id": result.task_id,
        "status": "completed" if result.success else "failed",
        "economics": tracker.get_status()
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
