import aiosqlite
from enum import Enum
from typing import Optional, Any
from contextlib import asynccontextmanager

from ..logging import get_logger

logger = get_logger(__name__)


class MessageType(Enum):
    USER = "user"
    AI = "ai"


class DatabaseException(Exception):
    """Raised when database operation fails"""

    pass


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
            logger.warning(
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
            logger.warning(
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
        self,
        user_id: str,
        thread_id: str,
        title: str,
        last_llm_used: str,
        project_id: Optional[str] = None,
    ) -> None:
        try:
            # Transaction handled externally for commit.
            await self.conn.execute(
                """INSERT INTO user_threads (user_id, thread_id, title, last_llm_used, project_id)
                    VALUES(?, ?, ?, ?, ?)
                    ON CONFLICT(thread_id) DO NOTHING""",
                (user_id, thread_id, title, last_llm_used, project_id),
            )
            return
        except aiosqlite.IntegrityError as e:
            logger.warning(
                "Create user thread failed - integrity constraint | user_id: %s | thread_id: %s | error: %s",
                user_id,
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database integrity error: {e}") from e
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

    async def set_thread_updated(
        self, user_id: str, thread_id: str, last_llm_used: str
    ) -> None:
        try:
            # Transaction handled externally for commit.
            await self.conn.execute(
                """UPDATE user_threads SET updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), last_llm_used = ?
                    WHERE user_id = ? AND thread_id = ?""",
                (last_llm_used, user_id, thread_id),
            )
            return
        except aiosqlite.IntegrityError as e:
            logger.warning(
                "Set thread updated_at failed - integrity constraint | user_id: %s | thread_id: %s",
                user_id,
                thread_id,
            )
            raise DatabaseException(f"Database integrity error: {e}") from e
        except aiosqlite.OperationalError as e:
            logger.error(
                "Set thread updated_at failed - operational error | user_id: %s | thread_id: %s | error: %s",
                user_id,
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Set thread updated_at failed - database error | user_id: %s | thread_id: %s | error: %s",
                user_id,
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Set thread updated_at failed - unexpected error | user_id: %s | thread_id: %s",
                user_id,
                thread_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

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

    async def thread_exists(self, thread_id: str) -> bool:
        try:
            async with self.conn.execute(
                """SELECT 1 FROM user_threads
                WHERE thread_id = ?""",
                (thread_id,),
            ) as cursor:
                res = await cursor.fetchone()
                return res is not None
        except aiosqlite.OperationalError as e:
            logger.error(
                "Thread exists check failed - operational error | thread_id: %s | error: %s",
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Thread exists check failed - database error | thread_id: %s | error: %s",
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Thread exists check failed - unexpected error | thread_id: %s",
                thread_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def create_thread_msg(
        self, content: str, msg_type: str, llm: str, msg_id: str, thread_id: str
    ) -> None:
        try:
            # Transaction handled externally for commit.
            await self.conn.execute(
                """INSERT INTO thread_messages 
                   (content, message_type, llm, message_index, message_id, thread_id)
                    SELECT ?, ?, ?, 
                       COALESCE(MAX(message_index), 0) + 1,
                       ?, ?
                    FROM thread_messages 
                    WHERE thread_id = ?
                    ON CONFLICT(thread_id, message_id) DO NOTHING""",
                (content, msg_type, llm, msg_id, thread_id, thread_id),
            )
            return
        except aiosqlite.IntegrityError as e:
            logger.warning(
                "Create thread message failed - integrity constraint | thread_id: %s | message_id: %s | error: %s",
                thread_id,
                msg_id,
                str(e),
            )
            raise DatabaseException(f"Database integrity error: {e}") from e
        except aiosqlite.OperationalError as e:
            logger.error(
                "Create thread message failed - operational error | thread_id: %s | message_id: %s | error: %s",
                thread_id,
                msg_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Create thread message failed - database error | thread_id: %s | message_id: %s | error: %s",
                thread_id,
                msg_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Create thread message failed - unexpected error | thread_id: %s | message_id: %s",
                thread_id,
                msg_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def get_thread_msg_last_idx(self, thread_id: str) -> int:
        try:
            async with self.conn.execute(
                """SELECT message_index FROM thread_messages WHERE thread_id = ?
                ORDER BY message_index DESC""",
                (thread_id,),
            ) as cursor:
                res = await cursor.fetchone()
                return int(res[0]) if res else 0
        except aiosqlite.OperationalError as e:
            logger.error(
                "Get thread message last index failed - operational error | thread_id: %s | error: %s",
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Get thread message last index failed - database error | thread_id: %s | error: %s",
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Get thread message last index failed - unexpected error | thread_id: %s",
                thread_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def get_thread_messages(
        self, thread_id: str
    ) -> Optional[list[dict[str, Any]]]:
        try:
            async with self.conn.execute(
                """SELECT * FROM thread_messages WHERE thread_id = ?
                ORDER BY message_index""",
                (thread_id,),
            ) as cursor:
                res = await cursor.fetchall()
                return [dict(row) for row in res] if res else None
        except aiosqlite.OperationalError as e:
            logger.error(
                "Get thread messages failed - operational error | thread_id: %s | error: %s",
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Get thread messages failed - database error | thread_id: %s | error: %s",
                thread_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Get thread messages failed - unexpected error | thread_id: %s",
                thread_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def delete_thread(self, thread_id: str, user_id: str):
        try:
            async with self.transaction():
                await self.conn.execute(
                    "DELETE FROM user_threads WHERE thread_id = ? AND user_id = ?",
                    (thread_id, user_id),
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

    async def create_project(
        self, project_id: str, user_id: str, title: str, instructions: str = ""
    ) -> None:
        try:
            async with self.transaction():
                await self.conn.execute(
                    """INSERT INTO projects (id, user_id, title, instructions)
                    VALUES (?, ?, ?, ?)""",
                    (project_id, user_id, title, instructions),
                )
        except aiosqlite.IntegrityError as e:
            logger.warning(
                "Create project failed - integrity constraint | user_id: %s | project_id: %s | error: %s",
                user_id,
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database integrity error: {e}") from e
        except aiosqlite.OperationalError as e:
            logger.error(
                "Create project failed - operational error | user_id: %s | project_id: %s | error: %s",
                user_id,
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Create project failed - database error | user_id: %s | project_id: %s | error: %s",
                user_id,
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Create project failed - unexpected error | user_id: %s | project_id: %s",
                user_id,
                project_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def get_user_projects(self, user_id: str) -> Optional[list[dict[str, Any]]]:
        try:
            async with self.conn.execute(
                """SELECT * FROM projects WHERE user_id = ?
                ORDER BY updated_at DESC, created_at DESC""",
                (user_id,),
            ) as cursor:
                res = await cursor.fetchall()
                return [dict(row) for row in res] if res else None
        except aiosqlite.OperationalError as e:
            logger.error(
                "Get user projects failed - operational error | user_id: %s | error: %s",
                user_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Get user projects failed - database error | user_id: %s | error: %s",
                user_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Get user projects failed - unexpected error | user_id: %s", user_id
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def get_project_by_id(self, project_id: str) -> Optional[dict[str, Any]]:
        try:
            async with self.conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        except aiosqlite.OperationalError as e:
            logger.error(
                "Get project by id failed - operational error | project_id: %s | error: %s",
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Get project by id failed - database error | project_id: %s | error: %s",
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Get project by id failed - unexpected error | project_id: %s",
                project_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def verify_project_ownership(self, user_id: str, project_id: str) -> bool:
        try:
            async with self.conn.execute(
                """SELECT 1 FROM projects
                WHERE user_id = ? AND id = ?""",
                (user_id, project_id),
            ) as cursor:
                res = await cursor.fetchone()
                return res is not None
        except aiosqlite.OperationalError as e:
            logger.error(
                "Verify project ownership failed - operational error | user_id: %s | project_id: %s | error: %s",
                user_id,
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Verify project ownership failed - database error | user_id: %s | project_id: %s | error: %s",
                user_id,
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Verify project ownership failed - unexpected error | user_id: %s | project_id: %s",
                user_id,
                project_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def update_project(
        self,
        project_id: str,
        title: Optional[str] = None,
        instructions: Optional[str] = None,
    ) -> None:
        # NEED Transaction
        try:
            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)

            if instructions is not None:
                updates.append("instructions = ?")
                params.append(instructions)

            updates.append("updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))")

            if not updates:
                return

            params.append(project_id)
            query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ?"

            async with self.transaction():
                await self.conn.execute(query, tuple(params))
        except aiosqlite.IntegrityError as e:
            logger.warning(
                "Update project failed - integrity constraint | project_id: %s",
                project_id,
            )
            raise DatabaseException(f"Database integrity error: {e}") from e
        except aiosqlite.OperationalError as e:
            logger.error(
                "Update project failed - operational error | project_id: %s | error: %s",
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Update project failed - database error | project_id: %s | error: %s",
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Update project failed - unexpected error | project_id: %s",
                project_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def delete_project(self, project_id: str, user_id: str) -> None:
        try:
            async with self.transaction():
                await self.conn.execute(
                    "DELETE FROM projects WHERE id = ? AND user_id = ?",
                    (project_id, user_id),
                )
        except aiosqlite.OperationalError as e:
            logger.error(
                "Delete project failed - operational error | project_id: %s | error: %s",
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Delete project failed - database error | project_id: %s | error: %s",
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Delete project failed - unexpected error | project_id: %s",
                project_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def project_exists(self, project_id: str) -> bool:
        try:
            async with self.conn.execute(
                """SELECT 1 FROM projects
                WHERE id = ?""",
                (project_id,),
            ) as cursor:
                res = await cursor.fetchone()
                return res is not None
        except aiosqlite.OperationalError as e:
            logger.error(
                "Project exists check failed - operational error | project_id: %s | error: %s",
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Project exists check failed - database error | project_id: %s | error: %s",
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Project exists check failed - unexpected error | project_id: %s",
                project_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def get_project_threads(
        self, project_id: str
    ) -> Optional[list[dict[str, Any]]]:
        try:
            async with self.conn.execute(
                """SELECT * FROM user_threads WHERE project_id = ?
                ORDER BY updated_at DESC, created_at DESC""",
                (project_id,),
            ) as cursor:
                res = await cursor.fetchall()
                return [dict(row) for row in res] if res else None
        except aiosqlite.OperationalError as e:
            logger.error(
                "Get project threads failed - operational error | project_id: %s | error: %s",
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Get project threads failed - database error | project_id: %s | error: %s",
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Get project threads failed - unexpected error | project_id: %s",
                project_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e

    async def set_project_updated(self, project_id: str) -> None:
        try:
            async with self.transaction():
                await self.conn.execute(
                    """UPDATE projects SET updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                    WHERE id = ?""",
                    (project_id,),
                )
        except aiosqlite.IntegrityError as e:
            logger.warning(
                "Set project updated_at failed - integrity constraint | project_id: %s",
                project_id,
            )
            raise DatabaseException(f"Database integrity error: {e}") from e
        except aiosqlite.OperationalError as e:
            logger.error(
                "Set project updated_at failed - operational error | project_id: %s | error: %s",
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database operational error: {e}") from e
        except aiosqlite.DatabaseError as e:
            logger.error(
                "Set project updated_at failed - database error | project_id: %s | error: %s",
                project_id,
                str(e),
            )
            raise DatabaseException(f"Database error: {e}") from e
        except Exception as e:
            logger.exception(
                "Set project updated_at failed - unexpected error | project_id: %s",
                project_id,
            )
            raise DatabaseException(f"Unexpected database error: {e}") from e


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
        CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        instructions TEXT,
        updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_threads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        thread_id TEXT UNIQUE NOT NULL,
        title TEXT,
        last_llm_used TEXT,
        updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), 
        project_id TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) on DELETE CASCADE,
        FOREIGN KEY (project_id) REFERENCES projects(id) on DELETE CASCADE
        )
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS thread_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_index INTEGER NOT NULL,
        thread_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        llm TEXT,
        message_type TEXT NOT NULL CHECK(message_type IN ('user', 'ai')),
        content TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        FOREIGN KEY (thread_id) REFERENCES user_threads(thread_id) ON DELETE CASCADE,
        UNIQUE(thread_id, message_id),
        UNIQUE(thread_id, message_index)
        )
        """
    )

    # Users
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)")

    # Projects
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_projects_user_updated ON projects(user_id, updated_at DESC)"
    )

    # User Threads
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_threads_user_updated ON user_threads(user_id, updated_at DESC)"
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_threads_thread_id ON user_threads(thread_id)"
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_threads_project_updated ON user_threads(project_id, updated_at DESC)"
    )

    # Thread Messages
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_thread_messages_thread_id ON thread_messages(thread_id)"
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_thread_messages_index ON thread_messages(thread_id, message_index)"
    )

    await conn.commit()
    logger.info("App database initialized")
