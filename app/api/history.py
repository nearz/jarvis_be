from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .dependencies import (
    get_current_user,
    get_app_db,
    thread_validation,
    get_graph_saver,
)
from ..controllers.history import (
    history_controller,
    thread_message_history_controller,
    delete_thread_controller,
)
from ..models import User
from ..models.response_models import HistoryResponse, ThreadHistoryResponse
from ..core.db_ops.app_db import AppDatabase
from ..core.logging import get_logger
from .errors import create_error_response

logger = get_logger(__name__)
router = APIRouter()


@router.get("/history")
async def thread_history(
    user: User = Depends(get_current_user), app_db: AppDatabase = Depends(get_app_db)
):
    logger.info("History request | user_id: %s", user.id)
    result = await history_controller(user.id, app_db)

    if not result.success:
        logger.warning("History fetch failure | user_id: %s", user.id)
        return create_error_response(result)

    logger.info("History successfully fetched")
    if result.threads:
        return HistoryResponse(threads=result.threads)
    else:
        logger.info("No thread history")
        return HistoryResponse(threads=[])


@router.get("/history/{thread_id}")
async def thread_message_history(
    thread_id: str = Depends(thread_validation),
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
):
    result = await thread_message_history_controller(user.id, thread_id, app_db)

    if not result.success:
        logger.error(
            "Failed to fetch thread messages | thread_id: %s | user_id: %s",
            thread_id,
            user.id,
        )
        return create_error_response(result)

    # if result.success is True then result.messages should not be None.
    # Adding for type checker as well as a guard.
    if result.messages is None:
        logger.error(
            "Unexpected result.messages is None | thread_id: %s | user_id: %s",
            thread_id,
            user.id,
        )
        raise HTTPException(status_code=500, detail="Unexpected missing messages")

    logger.info(
        "Succesfully fetched thread messages | thread_id: %s | user_id: %s",
        thread_id,
        user.id,
    )
    return ThreadHistoryResponse(messages=result.messages)


@router.delete("/history/{thread_id}")
async def delete_thread(
    thread_id: str = Depends(thread_validation),
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
    saver: AsyncSqliteSaver = Depends(get_graph_saver),
):
    result = await delete_thread_controller(user.id, thread_id, app_db, saver)

    if not result.success:
        logger.error(
            "Failed to delete thread | thread_id: %s | user_id: %s",
            thread_id,
            user.id,
        )
        return create_error_response(result)

    logger.info(
        "Thread deleted succesfully | thread_id: %s | user_id: %s",
        thread_id,
        user.id,
    )
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "thread_id": thread_id,
        },
    )
