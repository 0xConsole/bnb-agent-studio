"""
SQLite persistence for agent activations.

Stores user activations of agents (hire records). On Vercel serverless,
SQLite lives in /tmp and resets on cold start — this is documented in the
README. The schema is simple: one table for activations.
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

_DB_PATH = os.environ.get("DB_PATH", "/tmp/bnb_agent_studio.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                category TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                created_at INTEGER NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def activate_agent(agent_id: str, agent_name: str, category: str, wallet: str) -> dict:
    """Record an agent activation (hire)."""
    init_db()
    conn = _get_conn()
    try:
        now = int(time.time())
        conn.execute(
            "INSERT INTO activations (agent_id, agent_name, category, wallet_address, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 'active', ?, ?)",
            (agent_id, agent_name, category, wallet, now, now),
        )
        conn.execute(
            "INSERT INTO agent_events (agent_id, event_type, event_data, created_at) VALUES (?, 'activation', ?, ?)",
            (agent_id, f"Agent {agent_name} activated by {wallet[:10]}...", now),
        )
        conn.commit()
        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "category": category,
            "wallet": wallet,
            "status": "active",
            "activated_at": now,
        }
    finally:
        conn.close()


def deactivate_agent(agent_id: str, wallet: str) -> dict:
    """Deactivate an agent."""
    init_db()
    conn = _get_conn()
    try:
        now = int(time.time())
        conn.execute(
            "UPDATE activations SET status = 'inactive', updated_at = ? WHERE agent_id = ? AND wallet_address = ?",
            (now, agent_id, wallet),
        )
        conn.execute(
            "INSERT INTO agent_events (agent_id, event_type, event_data, created_at) VALUES (?, 'deactivation', ?, ?)",
            (agent_id, f"Agent {agent_id} deactivated by {wallet[:10]}...", now),
        )
        conn.commit()
        return {"agent_id": agent_id, "status": "inactive", "updated_at": now}
    finally:
        conn.close()


def get_activations(wallet: str | None = None) -> list[dict]:
    """Get activations, optionally filtered by wallet."""
    init_db()
    conn = _get_conn()
    try:
        if wallet:
            rows = conn.execute(
                "SELECT * FROM activations WHERE wallet_address = ? ORDER BY created_at DESC",
                (wallet,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM activations ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_activation_count() -> int:
    """Total activations count."""
    init_db()
    conn = _get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM activations WHERE status = 'active'").fetchone()
        return row["cnt"] if row else 0
    except Exception:
        return 0
