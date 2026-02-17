from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Optional
import json
import os
import re
import uuid
import httpx
from duckduckgo_search import DDGS

app = FastAPI(title="ClawWork Cloud API + OpenClaw Research", version="2.1.0")

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

# Pydantic Models
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

class ResearchRequest(BaseModel):
    industry: str
    target_market: str = "global"
    specific_questions: Optional[str] = None

# OpenClaw Research Engine using duckduckgo-search library
def search_ddg(query: str, max_results: int = 8) -> List[Dict]:
    """Search DuckDuckGo using official library"""
    try:
        with DDGS() as ddgs:
            results = []
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
            return results
    except Exception as e:
        return [{"error": str(e), "title": "", "url": "", "snippet": f"Search error: {e}"}]

def run_research(industry: str, target_market: str) -> Dict:
    """Execute full market research pipeline"""
    task_id = f"research_{uuid.uuid4().hex[:8]}"
    tracker.track_cost(0.50)

    report = {
        "task_id": task_id,
        "industry": industry,
        "target_market": target_market,
        "generated_at": datetime.utcnow().isoformat(),
        "sections": {}
    }

    queries = {
        "market_overview": f"{industry} market size {target_market} 2026",
        "competitors": f"top {industry} companies {target_market}",
        "trends": f"{industry} trends forecast 2026 2027",
        "swot_signals": f"{industry} challenges opportunities {target_market}",
        "pricing": f"{industry} pricing strategy {target_market}",
    }

    for section_name, query in queries.items():
        results = search_ddg(query)
        findings = [r.get("snippet", "") for r in results if r.get("snippet") and "error" not in r]
        sources = [r.get("url", "") for r in results if r.get("url") and "error" not in r]
        report["sections"][section_name] = {
            "query": query,
            "sources": len(sources),
            "source_urls": sources[:5],
            "key_findings": findings[:5],
        }

    tracker.track_income(25.00)
    report["economics"] = tracker.get_status()
    return report

# API Endpoints
@app.get("/")
def root():
    return {"message": "ClawWork + OpenClaw API", "status": "active", "version": "2.1.0"}

@app.get("/status")
def get_status():
    return tracker.get_status()

@app.post("/task/start")
def start_task(task: BrowserTask):
    if task.estimated_cost:
        tracker.track_cost(task.estimated_cost)
    return {"task_id": task.task_id, "status": "started", "current_balance": round(tracker.balance, 2)}

@app.post("/task/complete")
def complete_task(result: TaskResult):
    if result.success:
        tracker.track_income(result.actual_revenue)
    else:
        tracker.tasks_failed += 1
    return {"task_id": result.task_id, "status": "completed" if result.success else "failed", "economics": tracker.get_status()}

@app.post("/research")
def do_research(req: ResearchRequest):
    """OpenClaw: Run automated market research"""
    report = run_research(req.industry, req.target_market)
    return report

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
