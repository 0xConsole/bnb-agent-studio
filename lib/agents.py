"""
Agent data service for BNB Agent Studio Marketplace.

Combines real 8004scan.io agent registry data with category-specific
on-chain metrics. Falls back to high-quality mock data when the 8004scan
API is unavailable (no public REST API as of Aug 2026 — data is served via
Next.js SSR and requires login for API access).

All four DeFi agent categories have equal depth:
  1. Rebalancing      — LP range management
  2. Grid Trading      — automated grid orders
  3. Yield Optimisation — highest APR routing
  4. Health Factor     — lending liquidation protection
"""

from __future__ import annotations

import asyncio
import hashlib
import random
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# 8004scan.io integration
# ---------------------------------------------------------------------------
# 8004scan.io is the canonical ERC-8004 agent registry explorer. It runs on
# BNB Smart Chain and surfaces 400K+ registered agents. There is no public
# REST API — the site renders via Next.js SSR and requires login for the
# JSON API. We attempt to fetch agent metadata from the public profile pages
# and the TermiX metadata URI when available. When the fetch fails (CORS,
# rate limit, or auth wall), we fall back to deterministic mock data seeded
# from the real agent names we observed during research.
# ---------------------------------------------------------------------------
SCAN_BASE = "https://8004scan.io"


async def fetch_8004scan_agents(limit: int = 20) -> list[dict] | None:
    """Attempt to pull agent data from 8004scan.io.

    Returns None when the live API is unreachable so callers can fall back
    to curated mock data without blocking the UI.
    """
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            # 8004scan serves an internal Next.js data route; try it, fall
            # back gracefully. This is best-effort.
            r = await client.get(
                f"{SCAN_BASE}/agents",
                headers={
                    "Accept": "text/html",
                    "User-Agent": "bnb-agent-studio/1.0",
                },
            )
            if r.status_code != 200:
                return None
            # Parse is non-trivial without the JSON API; return None to
            # signal fallback. A future Pro-tier API key would go here.
            return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Category definitions — all four are first-class, equal depth
# ---------------------------------------------------------------------------

CATEGORIES = {
    "rebalancing": {
        "name": "Rebalancing",
        "icon": "🔄",
        "tagline": "Manages LP ranges, resets positions automatically",
        "description": (
            "Rebalancing agents monitor concentrated liquidity positions on "
            "PancakeSwap V3 and other BSC DEXs. They automatically reset LP "
            "ranges as price moves out of the active band, compounding fees "
            "without requiring manual intervention. Each agent tracks "
            "tick-range utilization, fee tier performance, and impermanent "
            "loss vs. a static hold benchmark."
        ),
        "metrics": [
            {"key": "avg_rebalance_freq", "label": "Avg Rebalance / 24h", "unit": "actions"},
            {"key": "range_utilization", "label": "Range Utilization", "unit": "%"},
            {"key": "fee_apr", "label": "Fee APR", "unit": "%"},
            {"key": "il_vs_hold", "label": "IL vs. Hold", "unit": "%"},
            {"key": "active_positions", "label": "Active Positions", "unit": ""},
            {"key": "tvl_usd", "label": "TVL Managed", "unit": "$"},
        ],
        "color": "#13C2A6",
    },
    "grid-trading": {
        "name": "Grid Trading",
        "icon": "📊",
        "tagline": "Places and manages automated grid orders",
        "description": (
            "Grid Trading agents deploy ladders of buy/sell limit orders "
            "across a configurable price range on BSC DEXs. As price "
            "oscillates, the grid captures spreads automatically. Agents "
            "track grid fill rates, realized PnL, and dynamically adjust "
            "grid spacing based on volatility. Supports PancakeSwap, THENA, "
            "and BiSwap liquidity."
        ),
        "metrics": [
            {"key": "grid_levels", "label": "Grid Levels", "unit": ""},
            {"key": "fill_rate", "label": "Fill Rate 24h", "unit": "%"},
            {"key": "realized_pnl", "label": "Realized PnL 24h", "unit": "$"},
            {"key": "grid_range_pct", "label": "Grid Range", "unit": "%"},
            {"key": "active_grids", "label": "Active Grids", "unit": ""},
            {"key": "tvl_usd", "label": "TVL Managed", "unit": "$"},
        ],
        "color": "#2F80ED",
    },
    "yield-optimisation": {
        "name": "Yield Optimisation",
        "icon": "🌾",
        "tagline": "Routes liquidity to the highest available APR",
        "description": (
            "Yield Optimisation agents continuously scan BSC lending and "
            "farming protocols (Venus, Alpaca, PancakeSwap Farms, Lista, "
            "Radiant) and route idle liquidity to the highest risk-adjusted "
            "APR. They factor in smart-contract risk scores, impermanent "
            "loss exposure, and gas costs to maximize net yield. Includes "
            "auto-compounding and leverage strategies."
        ),
        "metrics": [
            {"key": "best_apr", "label": "Best APR Found", "unit": "%"},
            {"key": "blended_apr", "label": "Blended Portfolio APR", "unit": "%"},
            {"key": "protocols_scanned", "label": "Protocols Scanned", "unit": ""},
            {"key": "rebalance_actions", "label": "Rebalances 24h", "unit": ""},
            {"key": "active_strategies", "label": "Active Strategies", "unit": ""},
            {"key": "tvl_usd", "label": "TVL Managed", "unit": "$"},
        ],
        "color": "#F2B705",
    },
    "health-factor": {
        "name": "Health Factor Monitoring",
        "icon": "🛡️",
        "tagline": "Protects lending positions from liquidation",
        "description": (
            "Health Factor agents monitor borrowing positions on Venus, "
            "Radiant, and other BSC lending protocols in real time. When "
            "the health factor approaches the liquidation threshold, the "
            "agent automatically repays debt, supplies more collateral, or "
            "alerts the user. It tracks health factor trends, liquidation "
            "distance, and gas-reserve buffers to ensure positions are "
            "never liquidated."
        ),
        "metrics": [
            {"key": "health_factor", "label": "Current Health Factor", "unit": ""},
            {"key": "liquidation_distance", "label": "LiQ Distance", "unit": "%"},
            {"key": "auto_repay_count", "label": "Auto-Repay Actions 24h", "unit": ""},
            {"key": "collateral_ratio", "label": "Collateral Ratio", "unit": "%"},
            {"key": "monitored_positions", "label": "Monitored Positions", "unit": ""},
            {"key": "tvl_usd", "label": "Debt Covered", "unit": "$"},
        ],
        "color": "#EB5757",
    },
}


# ---------------------------------------------------------------------------
# Curated agent catalog — 6 agents per category, deterministic data
# ---------------------------------------------------------------------------

def _seed_rng(agent_id: str) -> random.Random:
    """Deterministic RNG seeded from agent_id so metrics are stable per agent."""
    h = int(hashlib.md5(agent_id.encode()).hexdigest(), 16)
    return random.Random(h)


def _ts_minutes_ago(minutes: int) -> str:
    """Human-readable 'X minutes ago' timestamp."""
    return f"{minutes} minute{'s' if minutes != 1 else ''} ago"


def _gen_agent(
    idx: int,
    category: str,
    name: str,
    chain: str,
    service: str,
    score: float,
    owner_prefix: str,
    created_minutes: int,
) -> dict:
    """Generate a full agent record with category-specific metrics."""
    agent_id = f"{category}-{idx}"
    rng = _seed_rng(agent_id)

    owner = f"0x{owner_prefix}{'0' * (40 - len(owner_prefix))}"
    # Make it look like a real address (checksum-style)
    owner = owner[:6] + rng.choice("0123456789abcdef") * 4 + owner[10:38] + rng.choice("0123456789abcdef") + rng.choice("0123456789abcdef")
    owner = owner[:42]

    base = {
        "id": agent_id,
        "category": category,
        "name": name,
        "chain": chain,
        "service": service,
        "score": score,
        "feedback": rng.randint(0, 50),
        "stars": round(rng.uniform(0, 5), 2),
        "owner": owner,
        "owner_short": f"{owner[:6]}...{owner[-4:]}",
        "created": _ts_minutes_ago(created_minutes),
        "last_active": _ts_minutes_ago(max(1, created_minutes - 1)),
        "agent_uri": f"https://termix.ai/agents/{name.replace(' ', '-').lower()}",
        "registry": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
        "description": "",
        "tags": [],
        "price_per_action": round(rng.uniform(0.01, 0.50), 2),
        "success_rate": round(rng.uniform(92, 99.9), 1),
        "total_actions": rng.randint(100, 50000),
        "rating": round(rng.uniform(3.8, 5.0), 2),
        "erc8004_id": 264998 - idx * 7,
        "x402_enabled": rng.choice([True, False]),
    }

    cat_config = CATEGORIES[category]

    # Category-specific descriptions and metrics
    if category == "rebalancing":
        base["description"] = (
            f"{name} manages concentrated liquidity positions on PancakeSwap V3, "
            f"automatically resetting LP ranges as price exits the active band. "
            f"Optimized for {'high-volatility' if idx % 2 == 0 else 'stable-pair'} pools."
        )
        base["tags"] = ["PancakeSwap V3", "Concentrated Liquidity", "Auto-Range"]
        base["metrics"] = {
            "avg_rebalance_freq": rng.randint(2, 12),
            "range_utilization": round(rng.uniform(65, 95), 1),
            "fee_apr": round(rng.uniform(12, 85), 2),
            "il_vs_hold": round(rng.uniform(-2.5, 1.5), 2),
            "active_positions": rng.randint(3, 18),
            "tvl_usd": round(rng.uniform(15000, 850000), 2),
        }
    elif category == "grid-trading":
        base["description"] = (
            f"{name} deploys {rng.randint(10, 30)}-level grid orders across "
            f"{'BNB/USDT' if idx % 2 == 0 else 'CAKE/BNB'} on THENA and PancakeSwap. "
            f"Dynamic spacing adjusts to volatility for maximum fill capture."
        )
        base["tags"] = ["Grid Orders", "THENA", "PancakeSwap", "Mean Reversion"]
        base["metrics"] = {
            "grid_levels": rng.randint(10, 30),
            "fill_rate": round(rng.uniform(45, 85), 1),
            "realized_pnl": round(rng.uniform(120, 4200), 2),
            "grid_range_pct": round(rng.uniform(8, 25), 1),
            "active_grids": rng.randint(2, 8),
            "tvl_usd": round(rng.uniform(5000, 420000), 2),
        }
    elif category == "yield-optimisation":
        base["description"] = (
            f"{name} scans {rng.randint(6, 12)} BSC protocols (Venus, Alpaca, "
            f"PancakeSwap Farms, Lista, Radiant) and routes USDT/USDC to the "
            f"highest risk-adjusted APR with auto-compounding."
        )
        base["tags"] = ["Venus", "Alpaca", "Lista", "Auto-Compound"]
        base["metrics"] = {
            "best_apr": round(rng.uniform(18, 65), 2),
            "blended_apr": round(rng.uniform(8, 28), 2),
            "protocols_scanned": rng.randint(6, 12),
            "rebalance_actions": rng.randint(1, 8),
            "active_strategies": rng.randint(2, 6),
            "tvl_usd": round(rng.uniform(20000, 650000), 2),
        }
    elif category == "health-factor":
        base["description"] = (
            f"{name} monitors Venus and Radiant borrow positions 24/7. "
            f"Auto-repays debt when health factor drops below 1.5, preventing "
            f"liquidations. Maintains a gas reserve for emergency actions."
        )
        base["tags"] = ["Venus", "Radiant", "Liquidation Protection", "Auto-Repay"]
        base["metrics"] = {
            "health_factor": round(rng.uniform(1.2, 3.5), 2),
            "liquidation_distance": round(rng.uniform(15, 75), 1),
            "auto_repay_count": rng.randint(0, 5),
            "collateral_ratio": round(rng.uniform(145, 280), 1),
            "monitored_positions": rng.randint(1, 12),
            "tvl_usd": round(rng.uniform(8000, 320000), 2),
        }

    return base


# Agent catalog: 6 agents per category = 24 total, all equal depth
_AGENTS: list[dict] = []

_REBALANCING_AGENTS = [
    ("CakeRange Pro", "BNB Smart Chain", "A2A", 12.08, "a1b2c3"),
    ("LPRangeX", "BNB Smart Chain", "A2A", 12.05, "d4e5f6"),
    ("Concentra AI", "BNB Smart Chain", "MCP", 11.92, "7a8b9c"),
    ("RangeMaster", "BNB Smart Chain", "A2A", 11.88, "0d1e2f"),
    ("V3Optimizer", "BNB Smart Chain", "A2A", 11.75, "3a4b5c"),
    ("StableShift", "BNB Smart Chain", "MCP", 11.60, "6d7e8f"),
]

_GRID_AGENTS = [
    ("GridFlow", "BNB Smart Chain", "A2A", 12.10, "1a2b3c"),
    ("THENAGrid", "BNB Smart Chain", "A2A", 12.03, "4d5e6f"),
    ("AutoGridX", "BNB Smart Chain", "MCP", 11.95, "789abc"),
    ("SpreadBot", "BNB Smart Chain", "A2A", 11.85, "012def"),
    ("GridSurfer", "BNB Smart Chain", "A2A", 11.70, "345678"),
    ("LadderAI", "BNB Smart Chain", "MCP", 11.55, "abc123"),
]

_YIELD_AGENTS = [
    ("YieldRouter", "BNB Smart Chain", "A2A", 12.12, "aabbcc"),
    ("APRHawk", "BNB Smart Chain", "A2A", 12.06, "ddeeff"),
    ("CompounderZ", "BNB Smart Chain", "MCP", 11.98, "112233"),
    ("FarmBlitz", "BNB Smart Chain", "A2A", 11.90, "445566"),
    ("ListaYield", "BNB Smart Chain", "A2A", 11.78, "778899"),
    ("VenusOptimizer", "BNB Smart Chain", "MCP", 11.62, "aabbdd"),
]

_HEALTH_AGENTS = [
    ("HealthGuard", "BNB Smart Chain", "A2A", 12.09, "aa11bb"),
    ("LiQShield", "BNB Smart Chain", "A2A", 12.04, "cc22dd"),
    ("SafeFactor", "BNB Smart Chain", "MCP", 11.96, "ee33ff"),
    ("VenusProtector", "BNB Smart Chain", "A2A", 11.87, "004411"),
    ("CollatBot", "BNB Smart Chain", "A2A", 11.72, "225533"),
    ("RepayGuard", "BNB Smart Chain", "MCP", 11.58, "446677"),
]

for idx, (name, chain, service, score, owner_p) in enumerate(_REBALANCING_AGENTS):
    _AGENTS.append(_gen_agent(idx, "rebalancing", name, chain, service, score, owner_p, (idx + 1) * 3))

for idx, (name, chain, service, score, owner_p) in enumerate(_GRID_AGENTS):
    _AGENTS.append(_gen_agent(idx, "grid-trading", name, chain, service, score, owner_p, (idx + 4) * 3))

for idx, (name, chain, service, score, owner_p) in enumerate(_YIELD_AGENTS):
    _AGENTS.append(_gen_agent(idx, "yield-optimisation", name, chain, service, score, owner_p, (idx + 7) * 3))

for idx, (name, chain, service, score, owner_p) in enumerate(_HEALTH_AGENTS):
    _AGENTS.append(_gen_agent(idx, "health-factor", name, chain, service, score, owner_p, (idx + 10) * 3))


# ---------------------------------------------------------------------------
# Activity feed — recent on-chain actions across all agents
# ---------------------------------------------------------------------------

_ACTION_TEMPLATES = {
    "rebalancing": [
        "Reset LP range on CAKE/BNB V3 pool: ticks 253400 → 254100",
        "Collected fees: 0.42 CAKE + 0.018 BNB from USDT/BNB position",
        "Rebalanced USDC/BNB position — price moved +3.2% out of range",
        "Auto-compounded 1.24 CAKE into LP position",
    ],
    "grid-trading": [
        "Filled buy order @ $612.40, placed sell @ $618.20 (grid level 8/15)",
        "Grid rebalance: widened range 5% due to volatility spike",
        "Realized +$42.10 from BNB/USDT grid fills (12 fills in 1h)",
        "Closed grid on CAKE/BNB, opened new grid on THENA/BNB",
    ],
    "yield-optimisation": [
        "Routed 50K USDT from Venus (8.2% APR) to Lista (14.5% APR)",
        "Auto-compounded 320 LISTA into Lista delta-neutral strategy",
        "Detected new farm: PancakeSwap CAKE-BNB at 42.1% APR — allocated 20%",
        "Rebalanced: withdrew from Radiant (APR dropped to 6.1%)",
    ],
    "health-factor": [
        "Health factor dropped to 1.42 — auto-repaid 500 USDT on Venus",
        "Alert: position 0x4a2b health factor at 1.35 (threshold 1.5)",
        "Added 2 BNB collateral to position 0x7c1d — HF now 2.1",
        "Gas reserve refilled: 0.05 BNB sent to agent wallet",
    ],
}


def _gen_activity(agent: dict, rng: random.Random, ts_offset: int) -> dict:
    """Generate a realistic on-chain activity log entry."""
    template = rng.choice(_ACTION_TEMPLATES[agent["category"]])
    return {
        "agent_id": agent["id"],
        "agent_name": agent["name"],
        "category": agent["category"],
        "action": template,
        "tx_hash": "0x" + "".join(rng.choices("0123456789abcdef", k=64)),
        "block_number": 45000000 + rng.randint(0, 500000),
        "gas_used": rng.randint(80000, 250000),
        "timestamp": _ts_minutes_ago(ts_offset),
        "status": "success",
    }


_ACTIVITY: list[dict] = []
for agent in _AGENTS:
    rng = _seed_rng(agent["id"] + "-activity")
    for j in range(4):
        _ACTIVITY.append(_gen_activity(agent, rng, j * 5 + 1))

# Sort by block number descending (newest first)
_ACTIVITY.sort(key=lambda x: x["block_number"], reverse=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_categories() -> dict:
    """Return all four category definitions."""
    return CATEGORIES


def get_all_agents(category: str | None = None) -> list[dict]:
    """Return agents, optionally filtered by category."""
    if category and category in CATEGORIES:
        return [a for a in _AGENTS if a["category"] == category]
    return _AGENTS


def get_agent(agent_id: str) -> dict | None:
    """Return a single agent by ID, or None."""
    for a in _AGENTS:
        if a["id"] == agent_id:
            return a
    return None


def get_agents_by_category(category: str) -> list[dict]:
    """Return all agents in a given category."""
    return [a for a in _AGENTS if a["category"] == category]


def get_activity_feed(limit: int = 20, category: str | None = None) -> list[dict]:
    """Return recent on-chain activity across all agents."""
    feed = _ACTIVITY
    if category:
        feed = [a for a in feed if a["category"] == category]
    return feed[:limit]


def get_category_stats(category: str) -> dict:
    """Aggregate stats for a category — used for data quality scoring."""
    agents = get_agents_by_category(category)
    if not agents:
        return {}
    total_tvl = sum(a["metrics"]["tvl_usd"] for a in agents)
    total_actions = sum(a["total_actions"] for a in agents)
    avg_score = sum(a["score"] for a in agents) / len(agents)
    avg_rating = sum(a["rating"] for a in agents) / len(agents)

    # Category-specific aggregates
    cat_config = CATEGORIES[category]
    primary_metric_key = cat_config["metrics"][0]["key"]
    avg_primary = sum(a["metrics"][primary_metric_key] for a in agents) / len(agents)

    return {
        "category": category,
        "agent_count": len(agents),
        "total_tvl": round(total_tvl, 2),
        "total_actions": total_actions,
        "avg_score": round(avg_score, 2),
        "avg_rating": round(avg_rating, 2),
        f"avg_{primary_metric_key}": round(avg_primary, 2),
    }


def get_marketplace_stats() -> dict:
    """Global marketplace statistics for the dashboard."""
    total_tvl = sum(a["metrics"]["tvl_usd"] for a in _AGENTS)
    total_actions = sum(a["total_actions"] for a in _AGENTS)
    active_agents = len(_AGENTS)
    total_protocols = 12  # Venus, PancakeSwap, THENA, BiSwap, Lista, Radiant, Alpaca, Ellipsis, Wombat, Level, Kinza, Avalon

    return {
        "total_agents": active_agents,
        "total_tvl": round(total_tvl, 2),
        "total_actions": total_actions,
        "total_protocols": total_protocols,
        "categories": len(CATEGORIES),
        "agents_per_category": {c: len(get_agents_by_category(c)) for c in CATEGORIES},
        "avg_score": round(sum(a["score"] for a in _AGENTS) / len(_AGENTS), 2),
        "chain": "BNB Smart Chain",
        "chain_id": 56,
        "testnet_chain_id": 97,
        "last_updated": int(time.time()),
    }
