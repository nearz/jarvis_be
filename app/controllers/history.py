from enum import Enum
from typing import Optional
from pydantic import BaseModel


from ..core.db_ops.app_db import AppDatabase
from ..models import Thread
from ..core.logging import get_logger


logger = get_logger(__name__)


class HistoryErrorType(Enum):
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

    except Exception as e:
        logger.exception("System error")
        return HistoryResult(
            success=False,
            error_type=HistoryErrorType.SYSTEM_ERROR,
            error_details="unexpected system failure",
        )
