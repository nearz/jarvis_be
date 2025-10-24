from ..core.db_ops.app_db import AppDatabase, DatabaseException
from ..core.db_ops.agent_checkpoints_db import CheckpointDatabase
from ..models import Thread, ThreadMessage
from ..models.controller_models import (
    HistoryResult,
    ThreadMessagesResult,
    ThreadDeleteResult,
    ErrorType,
)
from ..core.logging import get_logger


logger = get_logger(__name__)


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
        logger.exception("Database exception occurred | user_id: %s", user_id)
        return HistoryResult(
            success=False,
            error_type=ErrorType.DATABASE_ERROR,
            error_details="Database exception occurred",
        )

    except Exception as e:
        logger.exception("System error")
        return HistoryResult(
            success=False,
            error_type=ErrorType.SYSTEM_ERROR,
            error_details="Unexpected system failure",
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
                error_type=ErrorType.DATABASE_ERROR,
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
        logger.exception("Database exception occurred | user_id: %s", user_id)
        return ThreadMessagesResult(
            success=False,
            error_type=ErrorType.DATABASE_ERROR,
            error_details="Database exception occurred",
        )

    except Exception as e:
        logger.exception("System error | user_id: %s", user_id)
        return ThreadMessagesResult(
            success=False,
            error_type=ErrorType.SYSTEM_ERROR,
            error_details="Unexpected system failure",
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
            "Database exception occurred | thread_id: %s | user_id: %s",
            thread_id,
            user_id,
        )
        return ThreadDeleteResult(
            success=False,
            error_type=ErrorType.DATABASE_ERROR,
            error_details="Database exception occurred",
        )

    except Exception as e:
        logger.exception("Exception occurred while deleting a thread")
        return ThreadDeleteResult(
            success=False,
            error_type=ErrorType.SYSTEM_ERROR,
            error_details="Unexpected system failure",
        )
