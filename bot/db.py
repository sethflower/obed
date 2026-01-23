from __future__ import annotations

import datetime as dt

import aiosqlite

CREATE_ORDERS_TABLE = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    department TEXT NOT NULL,
    order_date TEXT NOT NULL,
    delta INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


class OrderRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._connection = await aiosqlite.connect(self._db_path)
        await self._connection.execute("PRAGMA journal_mode=WAL;")
        await self._connection.execute(CREATE_ORDERS_TABLE)
        await self._connection.commit()

    async def close(self) -> None:
        if self._connection is None:
            return
        await self._connection.close()

    async def add_order(
        self,
        user_id: int,
        department: str,
        order_date: dt.date,
        delta: int,
        created_at: dt.datetime | None = None,
    ) -> None:
        if self._connection is None:
            raise RuntimeError("Database connection is not initialized")

        timestamp = (created_at or dt.datetime.utcnow()).isoformat()
        await self._connection.execute(
            """
            INSERT INTO orders (user_id, department, order_date, delta, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, department, order_date.isoformat(), delta, timestamp),
        )
        await self._connection.commit()

    async def get_total_for_department(
        self, department: str, order_date: dt.date
    ) -> int:
        if self._connection is None:
            raise RuntimeError("Database connection is not initialized")

        cursor = await self._connection.execute(
            """
            SELECT COALESCE(SUM(delta), 0)
            FROM orders
            WHERE department = ? AND order_date = ?
            """,
            (department, order_date.isoformat()),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return int(row[0] if row else 0)
