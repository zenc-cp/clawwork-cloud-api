from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
from datetime import datetime
import json
from typing import Optional, Dict
import openai

app = FastAPI(title="ClawWork Cloud API", version="1.0.0")

# Economic Tracking
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
            "status": "thriving" if self.balance > 50 else "surviving" if self.balance > 10 else "critical"
        }

tracker = EconomicTracker()

# Pydantic Models
class MarketResearchRequest(BaseModel):
    industry: str
    target_market: str
    specific_questions: Optional[str] = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict] = None

# AI Market Research Generator
async def generate_market_research(request: MarketResearchRequest) -> Dict:
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        prompt = f"""Generate a comprehensive market research report for:
        
Industry: {request.industry}
Target Market: {request.target_market}
{f'Specific Questions: {request.specific_questions}' if request.specific_questions else ''}

Provide:
1. Executive Summary
2. Market Overview & Size
3. Target Audience Analysis
4. Competitive Landscape
5. Key Trends & Opportunities
6. Recommendations

Format as a professional business report."""
        
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert market research analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Track costs (approximate)
        tokens_used = response.usage.total_tokens
        cost = (tokens_used / 1000) * 0.03  # GPT-4 pricing
        tracker.track_cost(cost)
        
        return {
            "report": response.choices[0].message.content,
            "tokens_used": tokens_used,
            "cost": round(cost, 4)
        }
        
    except Exception as e:
        tracker.tasks_failed += 1
        raise HTTPException(status_code=500, detail=str(e))

# API Endpoints
@app.get("/")
async def root():
    return {
        "service": "ClawWork Cloud API",
        "status": "operational",
        "version": "1.0.0",
        "economics": tracker.get_status()
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "balance": tracker.balance}

@app.get("/economics")
async def get_economics():
    return tracker.get_status()

@app.post("/api/generate-research")
async def generate_research(request: MarketResearchRequest, background_tasks: BackgroundTasks):
    task_id = f"task_{datetime.now().timestamp()}"
    
    try:
        result = await generate_market_research(request)
        
        # Track income (fixed price for basic research)
        income = 50.0
        tracker.track_income(income)
        
        return {
            "task_id": task_id,
            "status": "completed",
            "result": result,
            "economics": tracker.get_status()
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "failed",
            "error": str(e),
            "economics": tracker.get_status()
        }

@app.post("/webhook/fiverr")
async def fiverr_webhook(request: dict, background_tasks: BackgroundTasks):
    """Handle incoming Fiverr order webhooks"""
    try:
        # Extract order details
        industry = request.get("industry", "General Business")
        target_market = request.get("target_market", "General Audience")
        
        research_request = MarketResearchRequest(
            industry=industry,
            target_market=target_market
        )
        
        result = await generate_market_research(research_request)
        tracker.track_income(50.0)
        
        return {
            "status": "success",
            "message": "Order processed automatically",
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
