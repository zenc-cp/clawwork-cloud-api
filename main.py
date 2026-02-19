from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Optional
import json
import os
import re
import uuid
import time
import httpx
import hmac
import hashlib
import base64
import urllib.parse
import random
from duckduckgo_search import DDGS

app = FastAPI(title="ClawWork Cloud API + OpenClaw Research", version="3.0.0")              # Economic Tracker
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

# OpenClaw Research Engine v2.2 - single DDGS instance with delays
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

    ddgs = DDGS()
    for section_name, query in queries.items():
        try:
            results = list(ddgs.text(query, max_results=8))
            findings = [r.get("body", "") for r in results if r.get("body")]
            sources = [r.get("href", "") for r in results if r.get("href")]
            titles = [r.get("title", "") for r in results if r.get("title")]
            report["sections"][section_name] = {
                "query": query,
                "sources": len(sources),
                "source_urls": sources[:5],
                "source_titles": titles[:5],
                "key_findings": findings[:5],
            }
        except Exception as e:
            report["sections"][section_name] = {
                "query": query,
                "sources": 0,
                "source_urls": [],
                "source_titles": [],
                "key_findings": [f"Search error: {str(e)}"],
            }
        time.sleep(2)

    tracker.track_income(25.00)
    report["economics"] = tracker.get_status()
    return report

# API Endpoints
@app.get("/")
def root():
    return {"message": "ClawWork + OpenClaw API", "status": "active", "version": "2.2.0"}

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

# OAuth 1.0a helper for X API
def oauth_sign(method, url, params, consumer_secret, token_secret):
    sorted_params = sorted(params.items())
    param_str = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in sorted_params)
    base_str = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_str, safe='')}"
    signing_key = f"{urllib.parse.quote(consumer_secret, safe='')}&{urllib.parse.quote(token_secret, safe='')}"
    sig = base64.b64encode(hmac.new(signing_key.encode(), base_str.encode(), hashlib.sha1).digest()).decode()
    return sig

class TweetRequest(BaseModel):
    text: str

@app.post("/tweet")
async def post_tweet(req: TweetRequest):
    ck = os.getenv("X_CONSUMER_KEY", "")
    cs = os.getenv("X_CONSUMER_SECRET", "")
    at = os.getenv("X_ACCESS_TOKEN", "")
    ats = os.getenv("X_ACCESS_TOKEN_SECRET", "")
    if not all([ck, cs, at, ats]):
        raise HTTPException(status_code=500, detail="X API credentials not configured")
    api_url = "https://api.x.com/2/tweets"
    oauth_params = {
        "oauth_consumer_key": ck,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": at,
        "oauth_version": "1.0",
    }
    sig = oauth_sign("POST", api_url, oauth_params, cs, ats)
    oauth_params["oauth_signature"] = sig
    auth_parts = []
    for k, v in sorted(oauth_params.items()):
        auth_parts.append(f'{k}="{urllib.parse.quote(v, safe="")}"')
    auth_header = "OAuth " + ", ".join(auth_parts)
    async with httpx.AsyncClient() as client:
        resp = await client.post(api_url, json={"text": req.text}, headers={"Authorization": auth_header, "Content-Type": "application/json"})
    return {"status": resp.status_code, "response": resp.json()}

@app.get("/tweet")
async def get_tweet(text: str = "Hello from ClawWork!"):
    ck = os.getenv("X_CONSUMER_KEY", "")
    cs = os.getenv("X_CONSUMER_SECRET", "")
    at = os.getenv("X_ACCESS_TOKEN", "")
    ats = os.getenv("X_ACCESS_TOKEN_SECRET", "")
    if not all([ck, cs, at, ats]):
        raise HTTPException(status_code=500, detail="X API credentials not configured")
    api_url = "https://api.x.com/2/tweets"
    oauth_params = {
        "oauth_consumer_key": ck,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": at,
        "oauth_version": "1.0",
    }
    sig = oauth_sign("POST", api_url, oauth_params, cs, ats)
    oauth_params["oauth_signature"] = sig
    auth_parts = []
    for k, v in sorted(oauth_params.items()):
        auth_parts.append(f'{k}="{urllib.parse.quote(v, safe="")}"')
    auth_header = "OAuth " + ", ".join(auth_parts)
    async with httpx.AsyncClient() as client:
        resp = await client.post(api_url, json={"text": text}, headers={"Authorization": auth_header, "Content-Type": "application/json"})
    return {"status": resp.status_code, "response": resp.json()}


# Cybersecurity content templates for automated X posting
CYBER_TEMPLATES = [
    "Zero-day vulnerabilities don't wait for patches. Neither should your security team. Proactive defense > reactive response. #CyberSec #ZeroDay",
    "AI agents are transforming cybersecurity: automated threat detection, real-time response, continuous monitoring. The future is autonomous defense. #AIAgent #CyberSec",
    "Your API keys are your castle gates. Rotate them regularly, never hardcode them, always encrypt at rest. Basic hygiene saves enterprises. #APISecurity #InfoSec",
    "MITRE ATT&CK framework isn't just documentation - it's your defensive playbook. Map your defenses to known TTPs. #MITREATTACK #ThreatIntel",
    "Supply chain attacks increased 742% in 3 years. If you're not auditing your dependencies, you're trusting strangers with your keys. #SupplyChainSecurity",
    "The best security teams don't just find vulnerabilities - they understand business impact. Context-driven security wins every time. #RiskManagement #CISO",
    "Agentic AI introduces new attack surfaces: prompt injection, model poisoning, autonomous lateral movement. Secure your AI before it secures you. #AgenticAI #AISecurity",
    "Container escape, privilege escalation, lateral movement - cloud native doesn't mean cloud secure. Harden your K8s clusters. #CloudSecurity #Kubernetes",
    "Threat modeling isn't a one-time exercise. Your architecture evolves, so should your threat models. Continuous modeling = continuous security. #ThreatModeling",
    "MFA isn't optional anymore. Phishing-resistant MFA (FIDO2/WebAuthn) is the gold standard. Passwords alone are a liability. #MFA #IdentitySecurity",
]

@app.get("/scheduled-post")
async def scheduled_post():
    """Auto-generate and post cybersecurity content to X"""
    tweet_text = random.choice(CYBER_TEMPLATES)
    # Add timestamp variation to avoid duplicate detection
    hour = datetime.now().strftime("%H")
    if int(hour) < 12:
        tweet_text = tweet_text
    else:
        tweet_text = tweet_text.replace(".", "!", 1) if random.random() > 0.5 else tweet_text
    
    ck = os.getenv("X_CONSUMER_KEY", "")
    cs = os.getenv("X_CONSUMER_SECRET", "")
    at = os.getenv("X_ACCESS_TOKEN", "")
    ats = os.getenv("X_ACCESS_TOKEN_SECRET", "")
    if not all([ck, cs, at, ats]):
        return {"error": "X API credentials not configured"}
    api_url = "https://api.x.com/2/tweets"
    oauth_params = {
        "oauth_consumer_key": ck,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": at,
        "oauth_version": "1.0",
    }
    sig = oauth_sign("POST", api_url, oauth_params, cs, ats)
    oauth_params["oauth_signature"] = sig
    auth_parts = []
    for k, v in sorted(oauth_params.items()):
        auth_parts.append(f'{k}="{urllib.parse.quote(v, safe="")}"')
    auth_header = "OAuth " + ", ".join(auth_parts)
    async with httpx.AsyncClient() as client:
        resp = await client.post(api_url, json={"text": tweet_text}, headers={"Authorization": auth_header, "Content-Type": "application/json"})
    return {"status": resp.status_code, "posted": tweet_text, "response": resp.json()}

# ========== X ENGAGEMENT AUTOMATION (v3.0) ==========
# Helper: build OAuth header for any X API call
def build_oauth_header(method, url, extra_params=None):
    ck = os.getenv("X_CONSUMER_KEY", "")
    cs = os.getenv("X_CONSUMER_SECRET", "")
    at = os.getenv("X_ACCESS_TOKEN", "")
    ats = os.getenv("X_ACCESS_TOKEN_SECRET", "")
    if not all([ck, cs, at, ats]):
        return None, "X API credentials not configured"
    oauth_params = {
        "oauth_consumer_key": ck,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": at,
        "oauth_version": "1.0",
    }
    all_params = {**oauth_params}
    if extra_params:
        all_params.update(extra_params)
    sig = oauth_sign(method, url, all_params, cs, ats)
    oauth_params["oauth_signature"] = sig
    auth_parts = []
    for k, v in sorted(oauth_params.items()):
        auth_parts.append(f'{k}="{urllib.parse.quote(v, safe="")}"')
    return "OAuth " + ", ".join(auth_parts), None

# Get authenticated user ID
USER_ID = os.getenv("X_USER_ID", "15471332")

class ReplyRequest(BaseModel):
    tweet_id: str
    text: str

@app.post("/reply")
async def reply_to_tweet(req: ReplyRequest):
    """Reply to a specific tweet"""
    api_url = "https://api.x.com/2/tweets"
    auth_header, err = build_oauth_header("POST", api_url)
    if err:
        raise HTTPException(status_code=500, detail=err)
    payload = {"text": req.text, "reply": {"in_reply_to_tweet_id": req.tweet_id}}
    async with httpx.AsyncClient() as client:
        resp = await client.post(api_url, json=payload, headers={"Authorization": auth_header, "Content-Type": "application/json"})
    return {"status": resp.status_code, "response": resp.json()}

class LikeRequest(BaseModel):
    tweet_id: str

@app.post("/like")
async def like_tweet(req: LikeRequest):
    """Like a tweet"""
    api_url = f"https://api.x.com/2/users/{USER_ID}/likes"
    auth_header, err = build_oauth_header("POST", api_url)
    if err:
        raise HTTPException(status_code=500, detail=err)
    async with httpx.AsyncClient() as client:
        resp = await client.post(api_url, json={"tweet_id": req.tweet_id}, headers={"Authorization": auth_header, "Content-Type": "application/json"})
    return {"status": resp.status_code, "response": resp.json()}

class RetweetRequest(BaseModel):
    tweet_id: str

@app.post("/retweet")
async def retweet(req: RetweetRequest):
    """Retweet a tweet"""
    api_url = f"https://api.x.com/2/users/{USER_ID}/retweets"
    auth_header, err = build_oauth_header("POST", api_url)
    if err:
        raise HTTPException(status_code=500, detail=err)
    async with httpx.AsyncClient() as client:
        resp = await client.post(api_url, json={"tweet_id": req.tweet_id}, headers={"Authorization": auth_header, "Content-Type": "application/json"})
    return {"status": resp.status_code, "response": resp.json()}

@app.get("/mentions")
async def get_mentions(max_results: int = 10):
    """Fetch recent mentions (uses read quota - 100/month on Free tier)"""
    api_url = f"https://api.x.com/2/users/{USER_ID}/mentions"
    params = {"max_results": str(min(max_results, 100)), "tweet.fields": "created_at,author_id,conversation_id"}
    auth_header, err = build_oauth_header("GET", api_url, params)
    if err:
        raise HTTPException(status_code=500, detail=err)
    query_str = "&".join(f"{k}={urllib.parse.quote(v, safe='')}" for k, v in params.items())
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_url}?{query_str}", headers={"Authorization": auth_header})
    return {"status": resp.status_code, "response": resp.json()}

# Smart reply templates for engagement
REPLY_TEMPLATES = {
    "security": [
        "Great point on security! Defense-in-depth is always the way to go.",
        "This is crucial for any security team. Proactive beats reactive every time.",
        "Solid take. The threat landscape is evolving fast - staying ahead is key.",
    ],
    "ai": [
        "AI in cybersecurity is a game-changer. Autonomous detection is the future.",
        "The intersection of AI and security is where the real innovation happens.",
        "Agentic AI is reshaping how we think about defense. Exciting times.",
    ],
    "general": [
        "Interesting perspective! Would love to dive deeper on this.",
        "Thanks for sharing. This resonates with what we're building at OpenClaw.",
        "Well said. The community needs more discussions like this.",
    ],
}

@app.get("/engage-cycle")
async def engage_cycle():
    """Full engagement cycle: fetch mentions, auto-reply, auto-like"""
    results = {"mentions_fetched": 0, "replies_sent": 0, "likes_given": 0, "errors": []}
    # Step 1: Fetch mentions
    api_url = f"https://api.x.com/2/users/{USER_ID}/mentions"
    params = {"max_results": "5", "tweet.fields": "created_at,author_id,text"}
    auth_header, err = build_oauth_header("GET", api_url, params)
    if err:
        return {"error": err}
    query_str = "&".join(f"{k}={urllib.parse.quote(v, safe='')}" for k, v in params.items())
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_url}?{query_str}", headers={"Authorization": auth_header})
    if resp.status_code != 200:
        results["errors"].append(f"Mentions fetch failed: {resp.status_code} - {resp.text}")
        return results
    data = resp.json()
    mentions = data.get("data", [])
    results["mentions_fetched"] = len(mentions)
    # Step 2: For each mention, like + reply
    for mention in mentions[:3]:
        tweet_id = mention["id"]
        tweet_text = mention.get("text", "").lower()
        # Determine reply category
        if any(w in tweet_text for w in ["security", "threat", "vulnerability", "hack", "breach", "cyber"]):
            category = "security"
        elif any(w in tweet_text for w in ["ai", "agent", "model", "llm", "autonomous", "machine learning"]):
            category = "ai"
        else:
            category = "general"
        reply_text = random.choice(REPLY_TEMPLATES[category])
        # Like the mention
        try:
            like_url = f"https://api.x.com/2/users/{USER_ID}/likes"
            like_auth, _ = build_oauth_header("POST", like_url)
            if like_auth:
                like_resp = await client.post(like_url, json={"tweet_id": tweet_id}, headers={"Authorization": like_auth, "Content-Type": "application/json"})
                if like_resp.status_code in [200, 201]:
                    results["likes_given"] += 1
        except Exception as e:
            results["errors"].append(f"Like error: {str(e)}")
        # Reply to the mention
        try:
            reply_url = "https://api.x.com/2/tweets"
            reply_auth, _ = build_oauth_header("POST", reply_url)
            if reply_auth:
                reply_payload = {"text": reply_text, "reply": {"in_reply_to_tweet_id": tweet_id}}
                reply_resp = await client.post(reply_url, json=reply_payload, headers={"Authorization": reply_auth, "Content-Type": "application/json"})
                if reply_resp.status_code in [200, 201]:
                    results["replies_sent"] += 1
        except Exception as e:
            results["errors"].append(f"Reply error: {str(e)}")
    return results
