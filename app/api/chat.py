from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .dependencies import (
    get_app_graph,
    get_graph_saver,
    get_current_user,
    get_app_db,
    thread_validation,
)
from ..models.request_models import ChatRequest
from ..models import User
from ..controllers.chat import chat_controller
from ..core.db_ops.app_db import AppDatabase
from ..core.logging import get_logger
from .errors import create_error_response


logger = get_logger(__name__)
router = APIRouter()


# TODO: Stream chat response.
@router.post("/chat")
async def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
    graph=Depends(get_app_graph),
):
    logger.info("New chat | message len: %d | llm: %s", len(req.message), req.llm)
    result = await chat_controller(
        req.message, req.llm, user.id, app_db, graph, thread_id=None
    )

    if not result.success:
        logger.warning("New chat error | user_id: %s", user.id)
        return create_error_response(result)

    logger.info("New chat successful | thread id: %s", result.thread_id)
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "ai_message": result.message,
            "thread_id": result.thread_id,
        },
    )


@router.post("/chat/{thread_id}")
async def chat_thread(
    req: ChatRequest,
    thread_id: str = Depends(thread_validation),
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
    graph=Depends(get_app_graph),
):
    thread_id = thread_id.strip()
    logger.info("Chat thread request | thread_id: %s", thread_id)

    result = await chat_controller(
        req.message, req.llm, user.id, app_db, graph, thread_id=thread_id
    )

    if not result.success:
        logger.warning("Chat thread request error | thread_id: %s", thread_id)
        return create_error_response(result)

    logger.info("Chat thread request successful | thread_id: %s", thread_id)
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "ai_message": result.message,
            "thread_id": result.thread_id,
        },
    )
