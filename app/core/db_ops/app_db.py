import aiosqlite
from typing import Optional, Any
from contextlib import asynccontextmanager

from ..logging import get_logger

logger = get_logger(__name__)


class DatabaseException(Exception):
    """Raised when database operation fails"""

    pass


# TODO: Consider changes when moving to Postgres
class AppDatabase:
    def __init__(self, connection: aiosqlite.Connection):
        self.conn = connection
        self.conn.row_factory = aiosqlite.Row

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions.
        Automatically commits on success, rolls back on error.
        """
        try:
            yield
            await self.conn.commit()
        except BaseException as e:
            logger.debug(
                "Database transaction failed, rolling back: %s", type(e).__name__
            )
            try:
                await self.conn.rollback()
            except Exception as rollback_error:
                logger.exception("Rollback failed: %s", rollback_error)
            raise

    async def create_user(self, user_id: str, email: str, password: str) -> bool:
        try:
            async with self.transaction():
                await self.conn.execute(
                    """INSERT INTO users (id, email, password)
                    VALUES (?, ?, ?)""",
                    (user_id, email, password),
                )
            return True
        except aiosqlite.IntegrityError:
            logger.debug(
                "User creation failed - integrity constraint | email: %s", email
            )
            return False
        except aiosqlite.OperationalError as e:
            logger.error(
                "User creation failed - operational error | email: %s | error: %s",
                email,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "User creation failed - database error | email: %s | error: %s",
                email,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "User creation failed - unexpected error | email: %s", email
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def user_email_exists(self, email: str) -> bool:
        try:
            async with self.conn.execute(
                """SELECT 1 FROM users
                WHERE email = ?""",
                (email,),
            ) as cursor:
                res = await cursor.fetchone()
                return res is not None
        except aiosqlite.OperationalError as e:
            logger.error(
                "User email exists check failed - operational error | email: %s | error: %s",
                email,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "User email exists check failed - database error | email: %s | error: %s",
                email,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "User email exists check failed - unexpected error | email: %s", email
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def get_user_by_email(self, email: str) -> Optional[dict[str, Any]]:
        try:
            async with self.conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        except aiosqlite.OperationalError as e:
            logger.error(
                "Get user by email failed - operational error | email: %s | error: %s",
                email,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Get user by email failed - database error | email: %s | error: %s",
                email,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Get user by email failed - unexpected error | email: %s", email
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def get_user_by_id(self, user_id: str) -> Optional[dict[str, Any]]:
        try:
            async with self.conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        except aiosqlite.OperationalError as e:
            logger.error(
                "Get user by id failed - operational error | user_id: %s | error: %s",
                user_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Get user by id failed - database error | user_id: %s | error: %s",
                user_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Get user by id failed - unexpected error | user_id: %s", user_id
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    # No DatabaseExceptions: Leave as return False for any exceptions so does not block login.
    async def set_last_login(self, user_id: str) -> bool:
        try:
            async with self.transaction():
                await self.conn.execute(
                    "UPDATE users SET last_login = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) WHERE id = ?",
                    (user_id,),
                )
            return True
        except aiosqlite.IntegrityError:
            logger.debug(
                "Set last login failed - integrity constraint | user_id: %s", user_id
            )
            return False
        except aiosqlite.OperationalError as e:
            logger.error(
                "Set last login failed - operational error | user_id: %s | error: %s",
                user_id,
                str(e),
            )
            return False
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Set last login failed - database error | user_id: %s | error: %s",
                user_id,
                str(e),
            )
            return False
        except Exception as e:
            logger.exception(
                "Set last login failed - unexpected error | user_id: %s", user_id
            )
            return False

    async def create_user_thread(
        self, user_id: str, thread_id: str, title: Optional[str] = None
    ) -> bool:
        if title is None:
            title = "New Chat"
        try:
            async with self.transaction():
                await self.conn.execute(
                    """INSERT INTO user_threads (user_id, thread_id, title)
                    VALUES(?, ?, ?)""",
                    (user_id, thread_id, title),
                )
            return True
        except aiosqlite.IntegrityError:
            logger.debug(
                "Create user thread failed - integrity constraint | user_id: %s | thread_id: %s",
                user_id,
                thread_id,
            )
            return False
        except aiosqlite.OperationalError as e:
            logger.error(
                "Create user thread failed - operational error | user_id: %s | thread_id: %s | error: %s",
                user_id,
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Create user thread failed - database error | user_id: %s | thread_id: %s | error: %s",
                user_id,
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Create user thread failed - unexpected error | user_id: %s | thread_id: %s",
                user_id,
                thread_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def get_user_threads(self, user_id: str) -> Optional[list[dict[str, Any]]]:
        try:
            async with self.conn.execute(
                """SELECT * FROM user_threads WHERE user_id = ?
                ORDER BY updated_at DESC, created_at DESC""",
                (user_id,),
            ) as cursor:
                res = await cursor.fetchall()
                return [dict(row) for row in res] if res else None
        except aiosqlite.OperationalError as e:
            logger.error(
                "Get user threads failed - operational error | user_id: %s | error: %s",
                user_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Get user threads failed - database error | user_id: %s | error: %s",
                user_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Get user threads failed - unexpected error | user_id: %s", user_id
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    # No DatabaseExceptions: Leave as return False for any exceptions so does not block login.
    async def set_thread_updated_at(self, user_id: str, thread_id: str) -> bool:
        try:
            async with self.transaction():
                await self.conn.execute(
                    """UPDATE user_threads SET updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                    WHERE user_id = ? AND thread_id = ?""",
                    (user_id, thread_id),
                )
            return True
        except aiosqlite.IntegrityError:
            logger.debug(
                "Set thread updated_at failed - integrity constraint | user_id: %s | thread_id: %s",
                user_id,
                thread_id,
            )
            return False
        except aiosqlite.OperationalError as e:
            logger.error(
                "Set thread updated_at failed - operational error | user_id: %s | thread_id: %s | error: %s",
                user_id,
                thread_id,
                str(e),
            )
            return False
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Set thread updated_at failed - database error | user_id: %s | thread_id: %s | error: %s",
                user_id,
                thread_id,
                str(e),
            )
            return False
        except Exception as e:
            logger.exception(
                "Set thread updated_at failed - unexpected error | user_id: %s | thread_id: %s",
                user_id,
                thread_id,
            )
            return False

    async def verify_thread_ownership(self, user_id: str, thread_id: str) -> bool:
        try:
            async with self.conn.execute(
                """SELECT 1 FROM user_threads
                WHERE user_id = ? AND thread_id = ?""",
                (user_id, thread_id),
            ) as cursor:
                res = await cursor.fetchone()
                return res is not None
        except aiosqlite.OperationalError as e:
            logger.error(
                "Verify thread ownership failed - operational error | user_id: %s | thread_id: %s | error: %s",
                user_id,
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Verify thread ownership failed - database error | user_id: %s | thread_id: %s | error: %s",
                user_id,
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Verify thread ownership failed - unexpected error | user_id: %s | thread_id: %s",
                user_id,
                thread_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e


# TODO: Consider saving chat history to mirror langgraph checkpoints db
async def init_app_db(conn: aiosqlite.Connection):
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        last_login TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_threads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        thread_id TEXT NOT NULL,
        title TEXT DEFAULT 'New Chat',
        updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), 
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
