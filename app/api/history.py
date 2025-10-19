from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Union

from .dependencies import get_current_user, get_app_db, get_graph_saver
from ..controllers.history import (
    history_controller,
    thread_message_history_controller,
    HistoryErrorType,
    HistoryResult,
    ThreadMessagesResult,
)
from ..models import User, Thread
from ..models.response_models import HistoryResponse, ThreadHistoryResponse
from ..core.db_ops.app_db import AppDatabase
from ..core.db_ops.agent_checkpoints_db import thread_exists
from ..core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/history")
async def thread_history(
    user: User = Depends(get_current_user), app_db: AppDatabase = Depends(get_app_db)
):
    logger.info("History request | user_id: %s", user.id)
    result = await history_controller(user.id, app_db)

    if result.success:
        logger.info("History successfully fetched")
        if result.threads:
            return HistoryResponse(threads=result.threads)
        else:
            logger.info("No thread history")
            return HistoryResponse(threads=[])
    else:
        logger.warning("History fetch failure")
        return _create_error_response(result)


@router.get("/history/{thread_id}")
async def thread_message_history(
    thread_id: str,
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
    saver=Depends(get_graph_saver),
):
    thread_id = thread_id.strip()
    logger.info(
        "Thread message history request | thread_id: %s | user_id: %s",
        thread_id,
        user.id,
    )

    if not await thread_exists(saver, thread_id):
        logger.warning(
            "Thread does not exists | thread_id: %s | user_id: %s", thread_id, user.id
        )
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error_type": HistoryErrorType.VALIDATION_ERROR.value,
                "error_details": "Chat thread_id does not exist",
                "thread_id": thread_id,
            },
        )

    result = await thread_message_history_controller(user.id, thread_id, app_db)

    if result.success:
        logger.info(
            "Succesfully fetched thread messages | thread_id: %s | user_id: %s",
            thread_id,
            user.id,
        )
        if result.messages:
            return ThreadHistoryResponse(messages=result.messages)
    else:
        logger.error(
            "Failed to fetch thread messages | thread_id: %s | user_id: %s",
            thread_id,
            user.id,
        )
        return _create_error_response(result)


# TODO: Should I create a Base History Result?
def _create_error_response(
    result: Union[HistoryResult, ThreadMessagesResult],
) -> JSONResponse:
    """
    Maps ChatResult error types to HTTP status codes and returns formatted error response.
    """
    status_code_map = {
        HistoryErrorType.FORBIDDEN_ERROR: 403,
        HistoryErrorType.AUTHORIZATION_ERROR: 401,
        HistoryErrorType.DATABASE_ERROR: 503,
        HistoryErrorType.SYSTEM_ERROR: 500,
    }

    status_code = 400
    if result.error_type is not None:
        status_code = status_code_map.get(result.error_type, 400)

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error_type": result.error_type.value if result.error_type else None,
            "error_details": result.error_details,
        },
    )
