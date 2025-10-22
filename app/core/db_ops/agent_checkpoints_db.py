import aiosqlite
from contextlib import asynccontextmanager
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ..logging import get_logger

logger = get_logger(__name__)


class DatabaseException(Exception):
    """Raised when database operation fails"""

    pass


class CheckpointDatabase:
    def __init__(self, connection: aiosqlite.Connection):
        self.conn = connection

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

    async def delete_thread(self, thread_id: str):
        try:
            async with self.transaction():
                await self.conn.execute(
                    "DELETE FROM checkpoints WHERE thread_id = ?",
                    (thread_id,),
                )
                await self.conn.execute(
                    "DELETE FROM writes WHERE thread_id = ?",
                    (thread_id,),
                )
        except aiosqlite.OperationalError as e:
            logger.error(
                "Delete thread failed - operational error | thread_id: %s | error: %s",
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Delete thread failed - database error | thread_id: %s | error: %s",
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Delete thread failed - unexpected error | thread_id: %s",
                thread_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e
