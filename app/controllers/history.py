from enum import Enum
from typing import Optional
from pydantic import BaseModel


from ..core.db_ops.app_db import AppDatabase, DatabaseException
from ..core.db_ops.agent_checkpoints_db import CheckpointDatabase
from ..models import Thread, ThreadMessage
from ..core.logging import get_logger


logger = get_logger(__name__)


class HistoryErrorType(Enum):
    FORBIDDEN_ERROR = "forbidden_error"
    VALIDATION_ERROR = "validation_error"
    AUTHORIZATION_ERROR = "authorization_error"
    DATABASE_ERROR = "database_error"
    SYSTEM_ERROR = "system_error"


class HistoryResult:
    def __init__(
        self,
        success: bool,
        threads: Optional[list[Thread]] = None,
        error_type: Optional[HistoryErrorType] = None,
        error_details: Optional[str] = None,
    ):
        self.success = success
        self.threads = threads
        self.error_type = error_type
        self.error_details = error_details


class ThreadMessagesResult:
    def __init__(
        self,
        success: bool,
        messages: Optional[list[ThreadMessage]] = None,
        error_type: Optional[HistoryErrorType] = None,
        error_details: Optional[str] = None,
    ):
        self.success = success
        self.messages = messages
        self.error_type = error_type
        self.error_details = error_details


class ThreadDeleteResult:
    def __init__(
        self,
        success: bool,
        error_type: Optional[HistoryErrorType] = None,
        error_details: Optional[str] = None,
    ):
        self.success = success
        self.error_type = error_type
        self.error_details = error_details


async def history_controller(user_id: str, app_db: AppDatabase) -> HistoryResult:
    try:
        threads_db = await app_db.get_user_threads(user_id)

        if threads_db is None:
            logger.info("No thread history | user_id: %s", user_id)
            return HistoryResult(success=True)

        threads = [
            Thread(
                title=t["title"],
                thread_id=t["thread_id"],
                last_llm_used=t["last_llm_used"],
                created_at=t["created_at"],
                updated_at=t["updated_at"],
            )
            for t in threads_db
        ]
        logger.info(
            "Thread history fetched | user_id: %s | thread count: %d",
            user_id,
            len(threads),
        )

        return HistoryResult(success=True, threads=threads)

    except DatabaseException as e:
        logger.exception("Database exception occured | user_id: %s", user_id)
        return HistoryResult(
            success=False,
            error_type=HistoryErrorType.DATABASE_ERROR,
            error_details="Database exception occured",
        )

    except Exception as e:
        logger.exception("System error")
        return HistoryResult(
            success=False,
            error_type=HistoryErrorType.SYSTEM_ERROR,
            error_details="unexpected system failure",
        )


async def thread_message_history_controller(
    user_id: str, thread_id: str, app_db: AppDatabase
) -> ThreadMessagesResult:
    try:
        msgs_db = await app_db.get_thread_messages(thread_id)
        if msgs_db is None:
            logger.critical(
                "Data Inconsistency: Thread exists but has no messages | thread_id: %s | user_id: %s",
                thread_id,
                user_id,
            )
            return ThreadMessagesResult(
                success=False,
                error_type=HistoryErrorType.DATABASE_ERROR,
                error_details="Data inconsistency detected: thread exists but message history is missing",
            )

        msgs = [
            ThreadMessage(
                index=m["message_index"],
                content=m["content"],
                llm=m["llm"],
                message_type=m["message_type"],
                message_id=m["message_id"],
                thread_id=m["thread_id"],
                created_at=m["created_at"],
            )
            for m in msgs_db
        ]

        return ThreadMessagesResult(success=True, messages=msgs)

    except DatabaseException as e:
        logger.exception("Database exception occured | user_id: %s", user_id)
        return ThreadMessagesResult(
            success=False,
            error_type=HistoryErrorType.DATABASE_ERROR,
            error_details="Database exception occured",
        )

    except Exception as e:
        logger.exception("System error | user_id: %s", user_id)
        return ThreadMessagesResult(
            success=False,
            error_type=HistoryErrorType.SYSTEM_ERROR,
            error_details="unexpected system failure",
        )


async def delete_thread_controller(
    user_id: str,
    thread_id: str,
    app_db: AppDatabase,
    checkpoints_db: CheckpointDatabase,
) -> ThreadDeleteResult:
    try:
        await app_db.delete_thread(thread_id, user_id)
        await checkpoints_db.delete_thread(thread_id)

        return ThreadDeleteResult(success=True)

    except DatabaseException as e:
        logger.exception(
            "Database exception occured | thread_id: %s | user_id: %s",
            thread_id,
            user_id,
        )
        return ThreadDeleteResult(
            success=False,
            error_type=HistoryErrorType.DATABASE_ERROR,
            error_details="Database exception occured",
        )

    except Exception as e:
        logger.exception("Exception occured while deleting a threadlk ")
        return ThreadDeleteResult(
            success=False,
            error_type=HistoryErrorType.SYSTEM_ERROR,
            error_details="unexpected system failure",
        )
