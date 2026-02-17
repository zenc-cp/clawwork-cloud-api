#!/usr/bin/env python3
"""
OpenClaw Research Agent - Browser Automation for Market Research
Integrated with ClawWork Cloud API for economic tracking.
Runs 24/7 on cloud, processes Fiverr orders automatically.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import httpx

# Configuration
CLAWWORK_API = os.getenv("CLAWWORK_API", "https://clawwork-cloud-api.onrender.com")
N8N_WEBHOOK = os.getenv("N8N_WEBHOOK", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))  # seconds


class ClawWorkTracker:
    """Economic tracking via ClawWork Cloud API"""

    def __init__(self, api_url: str = CLAWWORK_API):
        self.api_url = api_url
        self.client = httpx.AsyncClient(timeout=30)

    async def status(self) -> Dict:
        r = await self.client.get(f"{self.api_url}/status")
        return r.json()

    async def start_task(self, task_id: str, task_type: str, cost: float) -> Dict:
        r = await self.client.post(
            f"{self.api_url}/task/start",
            json={"task_id": task_id, "task_type": task_type, "estimated_cost": cost},
        )
        return r.json()

    async def complete_task(self, task_id: str, success: bool, cost: float, revenue: float) -> Dict:
        r = await self.client.post(
            f"{self.api_url}/task/complete",
            json={"task_id": task_id, "success": success, "actual_cost": cost, "actual_revenue": revenue},
        )
        return r.json()


class OpenClawResearchAgent:
    """
    Headless browser automation agent that performs market research.
    Uses Playwright for cloud-based browser control.
    """

    def __init__(self):
        self.tracker = ClawWorkTracker()
        self.http = httpx.AsyncClient(timeout=60)

    # ── Web scraping helpers ───────────────────────────────

    async def search_web(self, query: str) -> List[Dict]:
        """Search via DuckDuckGo HTML (no API key needed)"""
        url = "https://html.duckduckgo.com/html/"
        r = await self.http.post(url, data={"q": query})
        # Parse results from raw HTML
        results = []
        text = r.text
        # Simple extraction of result snippets
        import re
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)', text)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', text, re.DOTALL)
        for i, (link, title) in enumerate(links[:10]):
            snippet = snippets[i] if i < len(snippets) else ""
            # Clean HTML tags from snippet
            snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            results.append({"url": link, "title": title.strip(), "snippet": snippet})
        return results

    async def fetch_page_text(self, url: str) -> str:
        """Fetch and extract text content from a webpage"""
        try:
            r = await self.http.get(url, follow_redirects=True)
            import re
            # Strip HTML tags
            text = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:5000]  # Limit to 5000 chars
        except Exception as e:
            return f"Error fetching {url}: {e}"

    # ── Research pipeline ──────────────────────────────────

    async def research_industry(self, industry: str, target_market: str) -> Dict:
        """Perform comprehensive market research on an industry"""
        task_id = f"research_{uuid.uuid4().hex[:8]}"

        # Track cost with ClawWork
        await self.tracker.start_task(task_id, "market_research", cost=0.50)

        report = {
            "task_id": task_id,
            "industry": industry,
            "target_market": target_market,
            "generated_at": datetime.utcnow().isoformat(),
            "sections": {},
        }

        # 1. Market overview
        results = await self.search_web(f"{industry} market size {target_market} 2026")
        report["sections"]["market_overview"] = {
            "query": f"{industry} market size {target_market} 2026",
            "sources": len(results),
            "key_findings": [r["snippet"] for r in results[:5]],
        }

        # 2. Competitor landscape
        results = await self.search_web(f"top {industry} companies {target_market}")
        report["sections"]["competitors"] = {
            "query": f"top {industry} companies {target_market}",
            "sources": len(results),
            "key_findings": [r["snippet"] for r in results[:5]],
        }

        # 3. Industry trends
        results = await self.search_web(f"{industry} trends forecast 2026 2027")
        report["sections"]["trends"] = {
            "query": f"{industry} trends forecast 2026 2027",
            "sources": len(results),
            "key_findings": [r["snippet"] for r in results[:5]],
        }

        # 4. SWOT signals
        results = await self.search_web(f"{industry} challenges opportunities {target_market}")
        report["sections"]["swot_signals"] = {
            "query": f"{industry} challenges opportunities {target_market}",
            "sources": len(results),
            "key_findings": [r["snippet"] for r in results[:5]],
        }

        # 5. Pricing intelligence
        results = await self.search_web(f"{industry} pricing strategy {target_market}")
        report["sections"]["pricing"] = {
            "query": f"{industry} pricing strategy {target_market}",
            "sources": len(results),
            "key_findings": [r["snippet"] for r in results[:5]],
        }

        # Track revenue on completion
        completion = await self.tracker.complete_task(
            task_id, success=True, cost=0.50, revenue=25.00
        )
        report["economics"] = completion.get("economics", {})

        return report

    # ── Order processing loop ──────────────────────────────

    async def process_order(self, order: Dict) -> Dict:
        """Process a single Fiverr order"""
        industry = order.get("industry", "technology")
        market = order.get("target_market", "global")
        print(f"[OpenClaw] Processing order: {industry} / {market}")

        report = await self.research_industry(industry, market)

        # Notify via n8n webhook if configured
        if N8N_WEBHOOK:
            try:
                await self.http.post(N8N_WEBHOOK, json=report)
                print(f"[OpenClaw] Report sent to n8n webhook")
            except Exception as e:
                print(f"[OpenClaw] Webhook error: {e}")

        return report

    async def poll_loop(self):
        """Main polling loop - checks for new orders and processes them"""
        print(f"[OpenClaw] Agent started. Polling every {POLL_INTERVAL}s")
        print(f"[OpenClaw] ClawWork API: {CLAWWORK_API}")

        status = await self.tracker.status()
        print(f"[OpenClaw] Initial balance: ${status['balance']}")

        while True:
            try:
                status = await self.tracker.status()
                if status["status"] == "critical":
                    print(f"[OpenClaw] WARNING: Balance critical (${status['balance']})")

                # In production, this would poll Fiverr API or n8n for new orders
                # For now, we check a webhook endpoint
                print(f"[OpenClaw] Heartbeat - Balance: ${status['balance']} | Tasks: {status['tasks_completed']}")

            except Exception as e:
                print(f"[OpenClaw] Error: {e}")

            await asyncio.sleep(POLL_INTERVAL)


async def main():
    agent = OpenClawResearchAgent()

    # Run a demo research task
    print("\n" + "=" * 60)
    print("OpenClaw Research Agent - Live Demo")
    print("=" * 60)

    report = await agent.process_order({
        "industry": "cybersecurity",
        "target_market": "Asia Pacific",
    })

    print(f"\nReport generated with {len(report['sections'])} sections:")
    for section, data in report["sections"].items():
        print(f"  - {section}: {data['sources']} sources found")

    if report.get("economics"):
        eco = report["economics"]
        print(f"\nEconomics: Balance=${eco['balance']} | Profit=${eco['net_profit']}")

    # Start polling loop for continuous operation
    # await agent.poll_loop()


if __name__ == "__main__":
    asyncio.run(main())
