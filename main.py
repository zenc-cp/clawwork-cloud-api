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

app = FastAPI(title="ClawWork Cloud API + OpenClaw Research", version="2.0.0")

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

# OpenClaw Research Engine
async def search_ddg(query: str) -> List[Dict]:
    """Search DuckDuckGo HTML for research data"""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.post("https://html.duckduckgo.com/html/", data={"q": query})
            results = []
            links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)', r.text)
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
            for i, (link, title) in enumerate(links[:8]):
                snippet = snippets[i] if i < len(snippets) else ""
                snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                results.append({"url": link, "title": title.strip(), "snippet": snippet})
            return results
        except Exception as e:
            return [{"error": str(e)}]

async def run_research(industry: str, target_market: str) -> Dict:
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
        results = await search_ddg(query)
        report["sections"][section_name] = {
            "query": query,
            "sources": len(results),
            "key_findings": [r.get("snippet", "") for r in results[:5] if r.get("snippet")],
        }

    tracker.track_income(25.00)
    report["economics"] = tracker.get_status()
    return report

# API Endpoints
@app.get("/")
def root():
    return {"message": "ClawWork + OpenClaw API", "status": "active", "version": "2.0.0"}

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
async def do_research(req: ResearchRequest):
    """OpenClaw: Run automated market research"""
    report = await run_research(req.industry, req.target_market)
    return report

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
