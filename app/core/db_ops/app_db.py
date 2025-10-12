import aiosqlite
from typing import Optional, Dict, Any

from ..logging import get_logger

logger = get_logger(__name__)


class AppDatabase:
    def __init__(self, connection: aiosqlite.Connection):
        self.conn = connection
        self.conn.row_factory = aiosqlite.Row

    async def create_user(self, user_id: str, email: str, password: str) -> bool:
        try:
            await self.conn.execute(
                """INSERT INTO users (id, email, password)
                VALUES (?, ?, ?)""",
                (user_id, email, password),
            )
            await self.conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        async with self.conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def user_email_exists(self, email: str) -> bool:
        async with self.conn.execute(
            """SELECT 1 FROM users
            WHERE email = ?""",
            (email,),
        ) as cursor:
            res = await cursor.fetchone()
            return res is not None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        async with self.conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_user_thread(
        self, user_id: str, thread_id: str, title: Optional[str] = None
    ) -> bool:
        try:
            await self.conn.execute(
                """INSERT INTO user_threads (user_id, thread_id, title)
                VALUES(?, ?, ?)""",
                (user_id, thread_id, title),
            )
            await self.conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def verify_thread_ownership(self, user_id: str, thread_id: str) -> bool:
        async with self.conn.execute(
            """SELECT 1 FROM user_threads
            WHERE user_id = ? AND thread_id = ?""",
            (user_id, thread_id),
        ) as cursor:
            res = await cursor.fetchone()
            return res is not None


# TODO: Create index on users id?
async def init_app_db(conn: aiosqlite.Connection):
    await conn.execute("PRAGMA foreigh_keys = ON")
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_threads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        thread_id TEXT NOT NULL,
        title TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) on DELETE CASCADE,
        UNIQUE(user_id, thread_id)
        )
        """
    )

    await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)")
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_threads_user_id ON user_threads(user_id)"
    )

    await conn.commit()
    logger.info("App database initialized")
