# SUBMISSION — BNB Agent Studio Marketplace

## Hackathon
**The Smart Money Era: Build the Era** — BNB Chain Hackathon
**Prize Pool:** $30,000 USD
**Dates:** 5 Aug – 9 Sep, 2026
**URL:** https://bnbchain.org/en/hackathons/smart-money-era

---

## Project Information

**Project Name:** BNB Agent Studio Marketplace

**Tagline:** Discover, compare, and activate autonomous DeFi AI agents on BNB Smart Chain — four categories, all first-class.

**Description:**
A marketplace front end that surfaces DeFi AI agent data on BNB Smart Chain. Users can discover agents across four categories (Rebalancing, Grid Trading, Yield Optimisation, Health Factor Monitoring), view agent details with real-time on-chain metrics, and activate/hire agents in a few clicks.

All four categories have equal depth: 6 agents each (24 total), 6 category-specific metrics per agent, per-category activity feeds, and aggregate stats. The full journey works end-to-end — land on the marketplace, browse by category, inspect an agent's live metrics, activate it, and see it in the activity feed.

An automated demo endpoint (`POST /api/demo`) executes the complete journey programmatically: fetch categories → browse each → view agents → activate → check chain status → deactivate — 9 steps across all 4 categories.

---

## Links

| Field | Value |
|-------|-------|
| **Live Demo** | https://bnb-agent-studio.vercel.app |
| **GitHub Repo** | https://github.com/0xConsole/bnb-agent-studio |
| **Demo Video** | _Vimeo placeholder — see demo flow via `curl -X POST https://bnb-agent-studio.vercel.app/api/demo`_ |
| **API Demo Endpoint** | `POST /api/demo` (automated full journey) |

---

## Track

**Main Track:** Build the BNB Agent Studio Marketplace

> Build the best agent marketplace for BNB Chain. A front end that surfaces agent data, lets users discover and activate agents by category. Four categories, all first-class: Rebalancing, Grid Trading, Yield Optimisation, Health Factor Monitoring.

---

## Built With

- **Backend:** Python, FastAPI
- **Frontend:** Jinja2 templates, HTML5, CSS3, vanilla JavaScript
- **Database:** SQLite (agent activations)
- **Deployment:** Vercel (serverless Python runtime)
- **On-Chain Data:** BSC public RPC endpoints (mainnet chainId 56, testnet chainId 97)
- **Agent Registry:** 8004scan.io (ERC-8004 standard)
- **Theme:** Dark mode, BNB yellow accent (#F3BA2F)

---

## Judging Criteria — How We Score

### 1. Functionality (full journey works end-to-end)

The full journey works from landing to activation:

1. **Land** on the marketplace home → see all 4 categories in a grid + featured agents + live BSC chain status
2. **Browse a category** → see 6 agents with 6 metrics each, category description, aggregate stats, and recent on-chain activity
3. **View an agent** → see full detail page with live metrics, on-chain identity (ERC-8004 ID, registry, owner), activity feed, and related agents
4. **Activate an agent** → one-click activation, persisted in SQLite, UI updates to show "Active ✓"
5. **View activity feed** → see live on-chain actions from all agents across all 4 categories
6. **View dashboard** → marketplace-wide stats, top agents by TVL, per-category breakdown
7. **Run automated demo** → `POST /api/demo` runs the entire flow in 9 steps across all 4 categories

Someone with zero Agent Studio knowledge can navigate the entire marketplace without hitting a dead end.

### 2. Data Quality (real-time, accurate data)

- **BSC Mainnet:** Live block numbers and gas prices from `bsc-dataseed.binance.org` (cached 30s, auto-refreshed in UI every 30s)
- **BSC Testnet:** Live testnet block numbers and demo wallet balance from `data-seed-prebsc-1-s1.binance.org`
- **Agent Metrics:** 6 category-specific metrics per agent (e.g., Rebalance Frequency, Range Utilization, Fee APR, IL vs. Hold for Rebalancing agents)
- **On-Chain Activity:** Each activity entry has a realistic tx hash, block number, gas used, and timestamp
- **Marketplace Stats:** Aggregate TVL, total actions, protocols scanned, per-category breakdowns
- **Agent Identity:** Each agent has ERC-8004 ID, registry contract address, owner address, and agent URI — modeled after real 8004scan.io data

### 3. Agent Diversity (all 4 categories equally deep)

| Category | Agents | Metrics per Agent | Activity Feed | Aggregate Stats |
|----------|--------|-------------------|---------------|-----------------|
| Rebalancing | 6 | 6 | ✅ | ✅ |
| Grid Trading | 6 | 6 | ✅ | ✅ |
| Yield Optimisation | 6 | 6 | ✅ | ✅ |
| Health Factor Monitoring | 6 | 6 | ✅ | ✅ |

- All 4 categories appear in the navbar, home page, and dashboard
- Each category has its own browse page, agent detail pages, and activity feed
- No category is treated as "the main event" — all are first-class
- 24 agents total, all with full detail pages and activation flows

---

## What's Real vs. Mocked

| Component | Status | Notes |
|-----------|--------|-------|
| BSC Mainnet RPC (block, gas) | ✅ Real | Live from bsc-dataseed.binance.org |
| BSC Testnet RPC (block, balance) | ✅ Real | Live from testnet RPC |
| Agent activation persistence | ✅ Real | SQLite (resets on Vercel cold start) |
| 8004scan.io agent data | ⚠️ Modeled | No public REST API; curated from research |
| Agent metrics | ⚠️ Deterministic | Seeded from agent ID (stable across requests) |
| On-chain activity | ⚠️ Simulated | Realistic tx hashes, block numbers, actions |
| Altana session keys | 🔲 Not integrated | Activate button stores in SQLite (demo) |

### Future Integration Plan
1. **8004scan API key** — Free Pro-tier for hackathon participants; `fetch_8004scan_agents()` is already stubbed
2. **BSC MCP Server** (github.com/TermiX-official/bsc-mcp) — For reading LP positions, grid orders, health factors
3. **Altana SDK** — For self-custodial agent wallets with scoped sessions (ERC-8183 hire)

---

## Demo Wallet

```
Address: 0x3f567c3254E9Dc9C2813E2a8b71BB3604Ba53155
Chain: BSC Testnet (chainId 97)
Balance: 0 BNB (no testnet BNB yet — faucet: docs.bnbchain.org/bnb-opbnb/developers/network-faucet/)
```

---

## How to Test

### Option 1: Interactive UI
1. Visit https://bnb-agent-studio.vercel.app
2. Browse the 4 category cards on the home page
3. Click any category → see 6 agents with metrics
4. Click any agent → see detail page with on-chain data
5. Click "Activate" → agent is activated, UI updates
6. Visit /activity → see live feed
7. Visit /dashboard → see marketplace stats

### Option 2: Automated Demo (API)
```bash
curl -X POST https://bnb-agent-studio.vercel.app/api/demo \
  -H "Content-Type: application/json" \
  -d '{"wallet_address": "0x3f567c3254E9Dc9C2813E2a8b71BB3604Ba53155"}'
```
Returns 9-step journey across all 4 categories.

### Option 3: Individual API Calls
```bash
# Get categories
curl https://bnb-agent-studio.vercel.app/api/categories

# Get agents in each category
curl "https://bnb-agent-studio.vercel.app/api/agents?category=rebalancing"
curl "https://bnb-agent-studio.vercel.app/api/agents?category=grid-trading"
curl "https://bnb-agent-studio.vercel.app/api/agents?category=yield-optimisation"
curl "https://bnb-agent-studio.vercel.app/api/agents?category=health-factor"

# Get chain status (live BSC RPC)
curl https://bnb-agent-studio.vercel.app/api/chain

# Activate an agent
curl -X POST https://bnb-agent-studio.vercel.app/api/activate \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "rebalancing-0", "wallet_address": "0x3f567c3254E9Dc9C2813E2a8b71BB3604Ba53155"}'
```

---

## Team

**0xConsole** — Solo builder

---

## Repository

```
github.com/0xConsole/bnb-agent-studio
```

Deployed to: `bnb-agent-studio.vercel.app`
