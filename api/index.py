"""
BNB Agent Studio Marketplace — FastAPI application.

A marketplace for DeFi AI agents on BNB Smart Chain with 4 categories:
Rebalancing, Grid Trading, Yield Optimisation, Health Factor Monitoring.

Endpoints:
  GET  /                      Marketplace home (category grid)
  GET  /category/{slug}       Browse agents by category
  GET  /agent/{agent_id}       Agent detail with on-chain data
  GET  /activity               Live activity feed
  GET  /dashboard              Marketplace stats dashboard
  POST /api/activate           Activate/hire an agent
  POST /api/deactivate         Deactivate an agent
  GET  /api/agents              List all agents (JSON)
  GET  /api/agents/{cat}       List agents by category (JSON)
  GET  /api/agent/{id}         Get single agent details (JSON)
  GET  /api/categories         List categories (JSON)
  GET  /api/activity           Activity feed (JSON)
  GET  /api/stats              Marketplace stats (JSON)
  GET  /api/chain              BSC chain status (JSON)
  GET  /api/health             Health check
  POST /api/demo               Automated demo flow (run full journey)
  GET  /api/activations        Get activations (JSON)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path bootstrap — Vercel runs with cwd=api/, local with cwd=repo root
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent  # api/
_ROOT = _HERE.parent                       # repo root
for _p in (_ROOT, _HERE):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from lib import agents as agent_service
from lib import onchain
from lib import db

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="BNB Agent Studio Marketplace",
    description="Discover and activate DeFi AI agents on BNB Smart Chain",
    version="1.0.0",
)

# Templates + static
_TEMPLATES_DIR = _ROOT / "templates"
_STATIC_DIR = _ROOT / "static"

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Initialize DB
db.init_db()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ActivateRequest(BaseModel):
    agent_id: str
    wallet_address: str


class DeactivateRequest(BaseModel):
    agent_id: str
    wallet_address: str


class DemoRequest(BaseModel):
    wallet_address: str = "0x3f567c3254E9Dc9C2813E2a8b71BB3604Ba53155"


# ---------------------------------------------------------------------------
# Page routes (Jinja2 templates)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Marketplace home — category grid + featured agents."""
    categories = agent_service.get_categories()
    stats = agent_service.get_marketplace_stats()
    featured = agent_service.get_all_agents()[:8]
    chain_status = await onchain.get_chain_status()
    return templates.TemplateResponse(request, "home.html", {
        "categories": categories,
        "stats": stats,
        "featured_agents": featured,
        "chain_status": chain_status,
    })


@app.get("/category/{slug}", response_class=HTMLResponse)
async def category_page(request: Request, slug: str):
    """Browse agents in a specific category."""
    categories = agent_service.get_categories()
    if slug not in categories:
        return RedirectResponse(url="/", status_code=302)

    cat_agents = agent_service.get_agents_by_category(slug)
    cat_config = categories[slug]
    cat_stats = agent_service.get_category_stats(slug)
    activity = agent_service.get_activity_feed(limit=10, category=slug)

    return templates.TemplateResponse(request, "category.html", {
        "category_slug": slug,
        "category": cat_config,
        "agents": cat_agents,
        "stats": cat_stats,
        "activity": activity,
        "categories": categories,
    })


@app.get("/agent/{agent_id}", response_class=HTMLResponse)
async def agent_detail(request: Request, agent_id: str):
    """Agent detail page with real-time on-chain data."""
    agent = agent_service.get_agent(agent_id)
    if not agent:
        return RedirectResponse(url="/", status_code=302)

    categories = agent_service.get_categories()
    cat_config = categories[agent["category"]]
    related_agents = [a for a in agent_service.get_agents_by_category(agent["category"]) if a["id"] != agent_id][:3]
    activity = agent_service.get_activity_feed(limit=5, category=agent["category"])
    chain_status = await onchain.get_chain_status()

    return templates.TemplateResponse(request, "agent_detail.html", {
        "agent": agent,
        "category": cat_config,
        "categories": categories,
        "related_agents": related_agents,
        "activity": activity,
        "chain_status": chain_status,
    })


@app.get("/activity", response_class=HTMLResponse)
async def activity_page(request: Request):
    """Live on-chain activity feed across all agents."""
    categories = agent_service.get_categories()
    activity = agent_service.get_activity_feed(limit=50)
    stats = agent_service.get_marketplace_stats()

    return templates.TemplateResponse(request, "activity.html", {
        "activity": activity,
        "categories": categories,
        "stats": stats,
    })


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Marketplace stats dashboard."""
    categories = agent_service.get_categories()
    stats = agent_service.get_marketplace_stats()
    chain_status = await onchain.get_chain_status()

    # Per-category stats
    cat_stats = {}
    for slug in categories:
        cat_stats[slug] = agent_service.get_category_stats(slug)

    # Top agents by TVL
    all_agents = sorted(agent_service.get_all_agents(), key=lambda a: a["metrics"]["tvl_usd"], reverse=True)
    top_agents = all_agents[:10]

    return templates.TemplateResponse(request, "dashboard.html", {
        "categories": categories,
        "stats": stats,
        "cat_stats": cat_stats,
        "top_agents": top_agents,
        "chain_status": chain_status,
        "activations": db.get_activation_count(),
    })


# ---------------------------------------------------------------------------
# JSON API endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": int(time.time()), "service": "bnb-agent-studio"}


@app.get("/api/categories")
async def api_categories():
    cats = agent_service.get_categories()
    return {slug: {k: v for k, v in cfg.items()} for slug, cfg in cats.items()}


@app.get("/api/agents")
async def api_agents(category: str | None = None):
    return {
        "agents": agent_service.get_all_agents(category),
        "count": len(agent_service.get_all_agents(category)),
    }


@app.get("/api/agent/{agent_id}")
async def api_agent(agent_id: str):
    agent = agent_service.get_agent(agent_id)
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return agent


@app.get("/api/activity")
async def api_activity(limit: int = 20, category: str | None = None):
    return {
        "activity": agent_service.get_activity_feed(limit=limit, category=category),
        "count": len(agent_service.get_activity_feed(limit=limit, category=category)),
    }


@app.get("/api/stats")
async def api_stats():
    return agent_service.get_marketplace_stats()


@app.get("/api/chain")
async def api_chain():
    return await onchain.get_chain_status()


@app.get("/api/activations")
async def api_activations(wallet: str | None = None):
    return {
        "activations": db.get_activations(wallet),
        "total_active": db.get_activation_count(),
    }


@app.post("/api/activate")
async def api_activate(req: ActivateRequest):
    agent = agent_service.get_agent(req.agent_id)
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    result = db.activate_agent(req.agent_id, agent["name"], agent["category"], req.wallet_address)
    return {"status": "activated", "activation": result, "agent": agent}


@app.post("/api/deactivate")
async def api_deactivate(req: DeactivateRequest):
    result = db.deactivate_agent(req.agent_id, req.wallet_address)
    return {"status": "deactivated", "result": result}


@app.post("/api/demo")
async def api_demo(req: DemoRequest):
    """Automated demo flow — runs the full journey end-to-end.

    1. Fetch categories
    2. Browse each category
    3. View an agent in each category
    4. Activate an agent
    5. Check chain status
    6. Deactivate
    """
    steps = []

    # Step 1: Get categories
    cats = agent_service.get_categories()
    steps.append({"step": 1, "action": "Fetch categories", "result": list(cats.keys()), "status": "ok"})

    # Step 2: Browse each category
    for slug in cats:
        cat_agents = agent_service.get_agents_by_category(slug)
        steps.append({"step": 2, "action": f"Browse {cats[slug]['name']}", "agent_count": len(cat_agents), "status": "ok"})

    # Step 3: View an agent in each category
    viewed_agents = []
    for slug in cats:
        cat_agents = agent_service.get_agents_by_category(slug)
        if cat_agents:
            agent = cat_agents[0]
            viewed_agents.append({"agent_id": agent["id"], "name": agent["name"], "category": slug})
    steps.append({"step": 3, "action": "View agents in each category", "agents_viewed": viewed_agents, "status": "ok"})

    # Step 4: Activate one agent (first from each category)
    activated = []
    for slug in cats:
        cat_agents = agent_service.get_agents_by_category(slug)
        if cat_agents:
            agent = cat_agents[0]
            result = db.activate_agent(agent["id"], agent["name"], agent["category"], req.wallet_address)
            activated.append({"agent_id": agent["id"], "name": agent["name"]})
    steps.append({"step": 4, "action": "Activate agents", "activated": activated, "status": "ok"})

    # Step 5: Check chain status
    chain = await onchain.get_chain_status()
    steps.append({"step": 5, "action": "Check BSC chain status", "mainnet_block": chain["mainnet"]["latest_block"], "testnet_block": chain["testnet"]["latest_block"], "status": "ok"})

    # Step 6: Deactivate
    for a in activated:
        db.deactivate_agent(a["agent_id"], req.wallet_address)
    steps.append({"step": 6, "action": "Deactivate agents", "deactivated": [a["agent_id"] for a in activated], "status": "ok"})

    return {
        "demo": "complete",
        "wallet": req.wallet_address,
        "steps": steps,
        "categories_covered": list(cats.keys()),
        "total_agents_interacted": len(viewed_agents),
        "timestamp": int(time.time()),
    }


# ---------------------------------------------------------------------------
# Fallback for SPA routes
# ---------------------------------------------------------------------------

@app.get("/{path:path}", response_class=HTMLResponse)
async def catch_all(request: Request, path: str):
    """Catch-all for unknown routes — redirect to home."""
    # Don't intercept static files or API routes
    if path.startswith("static/") or path.startswith("api/"):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return RedirectResponse(url="/", status_code=302)
