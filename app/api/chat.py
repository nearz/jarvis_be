from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .dependencies import get_app_graph, get_graph_saver, get_current_user
from ..models.request_models import ChatRequest
from ..models.user import User
from ..controllers.chat import chat_controller, ChatErrorType, ChatResult
from ..core.db_ops.agent_checkpoints_db import thread_exists
from ..core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter()

# TODO: Add pydantic response models, if applicable with streaming.


@router.post("/chat")
async def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    graph=Depends(get_app_graph),
):
    logger.info("New Chat | message len: %d | llm: %s", len(req.message), req.llm)
    result = await chat_controller(req.message, req.llm, graph, thread_id=None)

    if result.success:
        logger.info("Chat succesful | thread id: %s", result.thread_id)
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "ai_message": result.message,
                "thread_id": result.thread_id,
            },
        )
    else:
        logger.warning(
            "Chat failed | error_type: %s | error_details: %s",
            result.error_type.value,
            result.error_details,
        )
        return _create_error_response(result)


@router.post("/chat/{thread_id}")
async def chat_thread(
    thread_id: str,
    req: ChatRequest,
    user: User = Depends(get_current_user),
    graph=Depends(get_app_graph),
    saver=Depends(get_graph_saver),
):
    thread_id = thread_id.strip()
    logger.info("Chat thread request | thread_id: %s", thread_id)

    if not await thread_exists(saver, thread_id):
        logger.warning("Thread id not found | thread_id: %s", thread_id)
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error_type": ChatErrorType.VALIDATION_ERROR.value,
                "error_details": "Chat thread_id does not exist",
                "thread_id": thread_id,
            },
        )

    result = await chat_controller(req.message, req.llm, graph, thread_id=thread_id)

    if result.success:
        logger.info("Chat thread request succesful | thread_id: %s", thread_id)
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "ai_message": result.message,
                "thread_id": result.thread_id,
            },
        )
    else:
        logger.warning(
            "Chat thread request failed | error_type: %s | error_details: %s",
            result.error_type.value,
            result.error_details,
        )
        return _create_error_response(result)


def _create_error_response(result: ChatResult) -> JSONResponse:
    """
    Maps ChatResult error types to HTTP status codes and returns formatted error response.
    """
    # Map error types to status codes
    status_code_map = {
        ChatErrorType.VALIDATION_ERROR: 400,
        ChatErrorType.GRAPH_EXECUTION_ERROR: 502,
        ChatErrorType.RESPONSE_PROCESSING_ERROR: 502,
        ChatErrorType.SYSTEM_ERROR: 500,
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
            "thread_id": result.thread_id,
        },
    )
