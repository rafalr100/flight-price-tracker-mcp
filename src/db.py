"""
SQLite storage for the Flight Price Tracker MCP server.

Three tables:
  routes        — the routes the user wants to track (one row per route)
  snapshots     — every price reading, timestamped (many rows per route)
  airport_cache — maps IATA code → Skyscanner skyId + entityId
                  avoids repeated lookup API calls (1 lookup saved per check)
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "flights.db"
DB_PATH = Path(os.environ.get("FLIGHT_DB_PATH", _DEFAULT_PATH))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they do not yet exist."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS routes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                origin      TEXT NOT NULL,
                destination TEXT NOT NULL,
                depart_date TEXT NOT NULL,
                return_date TEXT NOT NULL DEFAULT '',
                label       TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL,
                UNIQUE(origin, destination, depart_date, return_date)
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id   INTEGER NOT NULL,
                price      REAL NOT NULL,
                currency   TEXT NOT NULL,
                carrier    TEXT NOT NULL DEFAULT '',
                checked_at TEXT NOT NULL,
                FOREIGN KEY(route_id) REFERENCES routes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS airport_cache (
                iata        TEXT PRIMARY KEY,
                sky_id      TEXT NOT NULL,
                entity_id   TEXT NOT NULL,
                name        TEXT NOT NULL DEFAULT '',
                cached_at   TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_route
                ON snapshots(route_id, checked_at);
            """
        )


# ── routes ──────────────────────────────────────────────────────────────────

def upsert_route(
    origin: str,
    destination: str,
    depart_date: str,
    return_date: str,
    label: str,
) -> int:
    """Insert a route, or return the existing id if already tracked."""
    with _connect() as conn:
        cur = conn.execute(
            "SELECT id FROM routes WHERE origin=? AND destination=? "
            "AND depart_date=? AND return_date=?",
            (origin, destination, depart_date, return_date),
        )
        row = cur.fetchone()
        if row:
            if label:
                conn.execute("UPDATE routes SET label=? WHERE id=?", (label, row["id"]))
            return int(row["id"])

        cur = conn.execute(
            "INSERT INTO routes (origin, destination, depart_date, return_date, label, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (origin, destination, depart_date, return_date, label,
             datetime.now(timezone.utc).isoformat()),
        )
        return int(cur.lastrowid)


def get_routes() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM routes ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_route_by_id(route_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM routes WHERE id=?", (route_id,)).fetchone()
        return dict(row) if row else None


# ── snapshots ────────────────────────────────────────────────────────────────

def insert_snapshot(route_id: int, price: float, currency: str, carrier: str = "") -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO snapshots (route_id, price, currency, carrier, checked_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (route_id, price, currency, carrier, datetime.now(timezone.utc).isoformat()),
        )


def get_snapshots(route_id: int) -> list[dict]:
    """Return all snapshots for a route, oldest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE route_id=? ORDER BY checked_at",
            (route_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── airport cache ─────────────────────────────────────────────────────────────

def get_airport(iata: str) -> dict | None:
    """Return cached Skyscanner IDs for an IATA code, or None if not cached."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM airport_cache WHERE iata=?", (iata.upper(),)
        ).fetchone()
        return dict(row) if row else None


def put_airport(iata: str, sky_id: str, entity_id: str, name: str = "") -> None:
    """Cache Skyscanner IDs for an IATA code (upsert)."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO airport_cache (iata, sky_id, entity_id, name, cached_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(iata) DO UPDATE SET "
            "sky_id=excluded.sky_id, entity_id=excluded.entity_id, "
            "name=excluded.name, cached_at=excluded.cached_at",
            (iata.upper(), sky_id, entity_id, name,
             datetime.now(timezone.utc).isoformat()),
        )
