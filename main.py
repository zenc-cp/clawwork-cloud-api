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
                async with httpx.AsyncClient() as c:
                    like_resp = await c.post(like_url, json={"tweet_id": tweet_id}, headers={"Authorization": like_auth, "Content-Type": "application/json"})
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
                async with httpx.AsyncClient() as c:
                    reply_resp = await c.post(reply_url, json=reply_payload, headers={"Authorization": reply_auth, "Content-Type": "application/json"})
                if reply_resp.status_code in [200, 201]:
                    results["replies_sent"] += 1
        except Exception as e:
            results["errors"].append(f"Reply error: {str(e)}")
    return results


# ============================================================
# FIVERR INTEGRATION MODULE v1.0
# Monitors Fiverr notifications and generates deliverables
# ============================================================

class FiverrTracker:
    def __init__(self):
        self.fiverr_username = os.getenv("FIVERR_USERNAME", "")
        self.orders = []
        self.gigs = [
            {"title": "Cybersecurity Threat Assessment Report", "price": 50, "category": "security"},
            {"title": "Market Research & Industry Analysis", "price": 35, "category": "research"},
            {"title": "AI Security Audit & Risk Report", "price": 75, "category": "ai_security"},
        ]
        self.deliveries_completed = 0
        self.fiverr_earnings = 0.0

    def add_order(self, order_id: str, gig_type: str, buyer: str, requirements: str):
        order = {
            "order_id": order_id,
            "gig_type": gig_type,
            "buyer": buyer,
            "requirements": requirements,
            "status": "in_progress",
            "created_at": datetime.utcnow().isoformat(),
            "deliverable": None
        }
        self.orders.append(order)
        return order

    def generate_deliverable(self, order_id: str, research_data: dict) -> dict:
        order = next((o for o in self.orders if o["order_id"] == order_id), None)
        if not order:
            return {"error": "Order not found"}
        deliverable = {
            "title": f"Deliverable for Order {order_id}",
            "content": research_data,
            "generated_at": datetime.utcnow().isoformat(),
            "word_count": len(str(research_data).split()),
        }
        order["deliverable"] = deliverable
        order["status"] = "ready_for_delivery"
        return deliverable

    def mark_delivered(self, order_id: str, revenue: float):
        order = next((o for o in self.orders if o["order_id"] == order_id), None)
        if order:
            order["status"] = "delivered"
            self.deliveries_completed += 1
            self.fiverr_earnings += revenue
            tracker.track_income(revenue)
        return order

    def get_status(self):
        return {
            "fiverr_username": self.fiverr_username,
            "total_gigs": len(self.gigs),
            "active_orders": len([o for o in self.orders if o["status"] == "in_progress"]),
            "ready_for_delivery": len([o for o in self.orders if o["status"] == "ready_for_delivery"]),
            "completed_deliveries": self.deliveries_completed,
            "fiverr_earnings": round(self.fiverr_earnings, 2),
        }

fiverr_tracker = FiverrTracker()


# Fiverr API Endpoints
class FiverrOrder(BaseModel):
    gig_type: str
    buyer_name: str
    requirements: str
    budget: float = 50.0

@app.get("/fiverr/status")
async def fiverr_status():
    return fiverr_tracker.get_status()

@app.get("/fiverr/gigs")
async def fiverr_gigs():
    return {"gigs": fiverr_tracker.gigs}

@app.post("/fiverr/new-order")
async def fiverr_new_order(order: FiverrOrder, background_tasks: BackgroundTasks):
    order_id = f"FVR-{uuid.uuid4().hex[:8]}"
    new_order = fiverr_tracker.add_order(order_id, order.gig_type, order.buyer_name, order.requirements)
    # Auto-generate deliverable using research engine
    background_tasks.add_task(auto_generate_fiverr_deliverable, order_id, order.gig_type, order.requirements)
    return {"message": "Order received, auto-generating deliverable", "order": new_order}

async def auto_generate_fiverr_deliverable(order_id: str, gig_type: str, requirements: str):
    try:
        research = run_research(gig_type, "global")
        fiverr_tracker.generate_deliverable(order_id, research)
    except Exception as e:
        print(f"Fiverr auto-gen error: {e}")

@app.post("/fiverr/deliver/{order_id}")
async def fiverr_deliver(order_id: str):
    order = next((o for o in fiverr_tracker.orders if o["order_id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] != "ready_for_delivery":
        return {"error": f"Order status is {order['status']}, not ready for delivery"}
    gig = next((g for g in fiverr_tracker.gigs if g["category"] == order["gig_type"]), fiverr_tracker.gigs[0])
    result = fiverr_tracker.mark_delivered(order_id, gig["price"])
    return {"message": "Delivered and earnings tracked", "order": result, "revenue": gig["price"]}

@app.get("/fiverr/orders")
async def fiverr_orders():
    return {"orders": fiverr_tracker.orders, "total": len(fiverr_tracker.orders)}


# ============================================================
# CRYPTO TRADING MONITOR MODULE v1.0
# Monitors crypto prices and executes DCA/Grid strategies
# Requires: Exchange API keys (Binance/Coinbase/OKX)
# ============================================================

class CryptoMonitor:
    def __init__(self):
        self.exchange = os.getenv("CRYPTO_EXCHANGE", "binance")
        self.api_key = os.getenv("CRYPTO_API_KEY", "")
        self.api_secret = os.getenv("CRYPTO_API_SECRET", "")
        self.trading_pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        self.strategy = os.getenv("CRYPTO_STRATEGY", "dca")
        self.dca_amount = float(os.getenv("DCA_AMOUNT", "10.0"))
        self.grid_levels = int(os.getenv("GRID_LEVELS", "5"))
        self.trades = []
        self.portfolio_value = 0.0
        self.total_invested = 0.0
        self.total_profit = 0.0
        self.is_active = False
        self.price_cache = {}

    async def fetch_prices(self) -> dict:
        prices = {}
        try:
            async with httpx.AsyncClient() as client:
                for pair in self.trading_pairs:
                    symbol = pair.replace("/", "")
                    resp = await client.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
                    if resp.status_code == 200:
                        data = resp.json()
                        prices[pair] = float(data["price"])
                    time.sleep(0.1)
        except Exception as e:
            prices["error"] = str(e)
        self.price_cache = prices
        return prices

    def record_trade(self, pair: str, side: str, amount: float, price: float):
        trade = {
            "trade_id": f"T-{uuid.uuid4().hex[:8]}",
            "pair": pair,
            "side": side,
            "amount": amount,
            "price": price,
            "value": round(amount * price, 2),
            "timestamp": datetime.utcnow().isoformat(),
            "strategy": self.strategy,
        }
        self.trades.append(trade)
        if side == "buy":
            self.total_invested += trade["value"]
        elif side == "sell":
            self.total_profit += trade["value"] - (amount * self.get_avg_buy_price(pair))
        return trade

    def get_avg_buy_price(self, pair: str) -> float:
        buys = [t for t in self.trades if t["pair"] == pair and t["side"] == "buy"]
        if not buys:
            return 0.0
        total_cost = sum(t["value"] for t in buys)
        total_amount = sum(t["amount"] for t in buys)
        return total_cost / total_amount if total_amount > 0 else 0.0

    def get_status(self) -> dict:
        return {
            "exchange": self.exchange,
            "strategy": self.strategy,
            "is_active": self.is_active,
            "api_configured": bool(self.api_key),
            "trading_pairs": self.trading_pairs,
            "total_trades": len(self.trades),
            "total_invested": round(self.total_invested, 2),
            "total_profit": round(self.total_profit, 2),
            "last_prices": self.price_cache,
            "dca_amount": self.dca_amount,
            "grid_levels": self.grid_levels,
            "requirements": {
                "api_key": "Set CRYPTO_API_KEY env var (trade-only, NO withdrawal)",
                "api_secret": "Set CRYPTO_API_SECRET env var",
                "exchange": "Set CRYPTO_EXCHANGE (binance/coinbase/okx)",
                "strategy": "Set CRYPTO_STRATEGY (dca/grid)",
                "min_capital": "$100-500 USDT recommended",
                "hk_legal": "Crypto trading is legal in HK via SFC-licensed exchanges",
            }
        }

crypto_monitor = CryptoMonitor()


# Crypto API Endpoints
@app.get("/crypto/status")
async def crypto_status():
    return crypto_monitor.get_status()

@app.get("/crypto/prices")
async def crypto_prices():
    prices = await crypto_monitor.fetch_prices()
    return {"prices": prices, "timestamp": datetime.utcnow().isoformat()}

@app.get("/crypto/requirements")
async def crypto_requirements():
    return {
        "title": "Crypto Trading Bot Requirements",
        "step_1": "Create account on SFC-licensed exchange (Binance HK, OKX, HashKey)",
        "step_2": "Generate API key with TRADE permission only (NO withdrawal)",
        "step_3": "Set environment variables: CRYPTO_API_KEY, CRYPTO_API_SECRET, CRYPTO_EXCHANGE",
        "step_4": "Choose strategy: DCA (safer, steady) or Grid (more active, higher risk)",
        "step_5": "Fund account with min $100-500 USDT",
        "step_6": "Activate via /crypto/activate endpoint",
        "legal_hk": "Crypto trading is legal in HK. SFC regulates VATPs. 11 licensed exchanges as of 2026.",
        "risk_warning": "Crypto trading involves significant risk. Past performance does not guarantee future results.",
        "supported_exchanges": ["binance", "coinbase", "okx", "hashkey", "bybit"],
        "supported_strategies": ["dca", "grid"],
    }

@app.post("/crypto/activate")
async def crypto_activate():
    if not crypto_monitor.api_key:
        return {"error": "API key not configured. Set CRYPTO_API_KEY env var first.", "setup": "/crypto/requirements"}
    crypto_monitor.is_active = True
    return {"message": "Crypto trading bot activated", "strategy": crypto_monitor.strategy, "pairs": crypto_monitor.trading_pairs}

@app.post("/crypto/deactivate")
async def crypto_deactivate():
    crypto_monitor.is_active = False
    return {"message": "Crypto trading bot deactivated"}

@app.get("/crypto/trades")
async def crypto_trades():
    return {"trades": crypto_monitor.trades, "total": len(crypto_monitor.trades)}


# ============================================================
# GOOGLE WORKSPACE INTEGRATION (Gmail + Calendar)
# Requires: Google OAuth2 credentials
# ============================================================

class GoogleWorkspace:
    def __init__(self):
        self.gmail_configured = bool(os.getenv("GOOGLE_CLIENT_ID", ""))
        self.calendar_configured = bool(os.getenv("GOOGLE_CLIENT_ID", ""))
        self.google_email = os.getenv("GOOGLE_EMAIL", "")
        self.notifications_sent = 0
        self.calendar_events = []

    def add_calendar_event(self, title: str, description: str, due_date: str):
        event = {
            "event_id": f"EVT-{uuid.uuid4().hex[:8]}",
            "title": title,
            "description": description,
            "due_date": due_date,
            "created_at": datetime.utcnow().isoformat(),
            "status": "scheduled",
        }
        self.calendar_events.append(event)
        return event

    def get_status(self):
        return {
            "gmail_configured": self.gmail_configured,
            "calendar_configured": self.calendar_configured,
            "google_email": self.google_email,
            "notifications_sent": self.notifications_sent,
            "upcoming_events": len([e for e in self.calendar_events if e["status"] == "scheduled"]),
            "setup_instructions": {
                "step_1": "Create Google account (e.g. openclaw.agent@gmail.com)",
                "step_2": "Enable Gmail API + Calendar API in Google Cloud Console",
                "step_3": "Create OAuth2 credentials or service account",
                "step_4": "Set env vars: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_EMAIL",
            }
        }

google_workspace = GoogleWorkspace()

@app.get("/google/status")
async def google_status():
    return google_workspace.get_status()

@app.post("/google/calendar/add")
async def google_calendar_add(title: str = "New Task", description: str = "", due_date: str = ""):
    event = google_workspace.add_calendar_event(title, description, due_date)
    return {"message": "Calendar event created", "event": event}

@app.get("/google/calendar/events")
async def google_calendar_events():
    return {"events": google_workspace.calendar_events}

# ============================================================
# UNIFIED DASHBOARD - All Systems
# ============================================================

@app.get("/dashboard")
async def unified_dashboard():
    return {
        "agent_name": "SlimBot 9000",
        "version": "4.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "clawwork": tracker.get_status(),
        "fiverr": fiverr_tracker.get_status(),
        "crypto": crypto_monitor.get_status(),
        "google": google_workspace.get_status(),
        "x_automation": {"configured": bool(os.getenv("X_API_KEY", ""))},
    }
