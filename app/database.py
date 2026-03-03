"""Simple async SQLite database layer via aiosqlite."""
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                e4_guid TEXT UNIQUE,
                counterparty_guid TEXT NOT NULL,
                delivery_point_guid TEXT NOT NULL,
                delivery_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Резервируется',
                stage TEXT NOT NULL DEFAULT 'Заказано',
                total_price REAL NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                product_guid TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                box_multiplicity INTEGER NOT NULL,
                net_weight REAL NOT NULL,
                gross_weight REAL NOT NULL
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


# ------------------------------------------------------------------
# Orders
# ------------------------------------------------------------------

async def get_orders(counterparty_guid: str) -> list[dict]:
    """List orders for a counterparty, newest first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM orders WHERE counterparty_guid = ? ORDER BY created_at DESC",
            (counterparty_guid,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_order(order_id: int) -> dict | None:
    """Get a single order with its items."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        order = dict(row)
        cursor = await db.execute(
            "SELECT * FROM order_items WHERE order_id = ?", (order_id,),
        )
        items = await cursor.fetchall()
        order["items"] = [dict(i) for i in items]
        return order


async def create_order(
    counterparty_guid: str,
    delivery_point_guid: str,
    delivery_date: str,
    items: list[dict],
    e4_guid: str | None = None,
) -> int:
    """Create an order with items. Returns new order id."""
    total_price = sum(i["price"] * i["quantity"] for i in items)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO orders
                (e4_guid, counterparty_guid, delivery_point_guid, delivery_date, total_price)
            VALUES (?, ?, ?, ?, ?)
            """,
            (e4_guid, counterparty_guid, delivery_point_guid, delivery_date, total_price),
        )
        order_id = cursor.lastrowid
        await db.executemany(
            """
            INSERT INTO order_items
                (order_id, product_guid, product_name, quantity, price,
                 box_multiplicity, net_weight, gross_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    order_id,
                    i["product_guid"],
                    i["product_name"],
                    i["quantity"],
                    i["price"],
                    i["box_multiplicity"],
                    i["net_weight"],
                    i["gross_weight"],
                )
                for i in items
            ],
        )
        await db.commit()
        return order_id


async def update_order(
    order_id: int,
    delivery_point_guid: str | None = None,
    delivery_date: str | None = None,
    items: list[dict] | None = None,
) -> None:
    """Update order fields and/or replace items."""
    async with aiosqlite.connect(DB_PATH) as db:
        if delivery_point_guid is not None:
            await db.execute(
                "UPDATE orders SET delivery_point_guid = ? WHERE id = ?",
                (delivery_point_guid, order_id),
            )
        if delivery_date is not None:
            await db.execute(
                "UPDATE orders SET delivery_date = ? WHERE id = ?",
                (delivery_date, order_id),
            )
        if items is not None:
            await db.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
            await db.executemany(
                """
                INSERT INTO order_items
                    (order_id, product_guid, product_name, quantity, price,
                     box_multiplicity, net_weight, gross_weight)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        order_id,
                        i["product_guid"],
                        i["product_name"],
                        i["quantity"],
                        i["price"],
                        i["box_multiplicity"],
                        i["net_weight"],
                        i["gross_weight"],
                    )
                    for i in items
                ],
            )
            total_price = sum(i["price"] * i["quantity"] for i in items)
            await db.execute(
                "UPDATE orders SET total_price = ? WHERE id = ?",
                (total_price, order_id),
            )
        await db.commit()


async def cancel_order(order_id: int) -> None:
    """Mark order as cancelled."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = 'Отменён' WHERE id = ?",
            (order_id,),
        )
        await db.commit()
