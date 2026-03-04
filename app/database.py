"""Simple async SQLite database layer via aiosqlite.

Stores only users (MAX user_id ↔ counterparty mapping).
Orders and all other data come from 1C on the fly.
"""
from __future__ import annotations

import aiosqlite

DB_PATH = "data.db"


async def init_db() -> None:
    """Create tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                max_user_id INTEGER UNIQUE NOT NULL,
                phone TEXT,
                counterparty_guid TEXT,
                counterparty_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


# ------------------------------------------------------------------
# Users
# ------------------------------------------------------------------

async def get_user_by_max_id(max_user_id: int) -> dict | None:
    """Find a user by their MAX messenger user_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE max_user_id = ?", (max_user_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def upsert_user(
    max_user_id: int,
    phone: str | None = None,
    counterparty_guid: str | None = None,
    counterparty_name: str | None = None,
) -> None:
    """Create or update a user record."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (max_user_id, phone, counterparty_guid, counterparty_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(max_user_id) DO UPDATE SET
                phone = COALESCE(excluded.phone, phone),
                counterparty_guid = COALESCE(excluded.counterparty_guid, counterparty_guid),
                counterparty_name = COALESCE(excluded.counterparty_name, counterparty_name)
            """,
            (max_user_id, phone, counterparty_guid, counterparty_name),
        )
        await db.commit()


async def set_counterparty(
    max_user_id: int,
    counterparty_guid: str,
    counterparty_name: str,
) -> None:
    """Set the selected counterparty for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET counterparty_guid = ?, counterparty_name = ? WHERE max_user_id = ?",
            (counterparty_guid, counterparty_name, max_user_id),
        )
        await db.commit()


async def get_user_by_counterparty_guid(counterparty_guid: str) -> dict | None:
    """Find a user by counterparty GUID (to send bot notification)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE counterparty_guid = ? LIMIT 1",
            (counterparty_guid,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
