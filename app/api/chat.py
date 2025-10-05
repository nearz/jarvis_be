from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from .dependencies import get_app_graph, get_graph_saver
from ..models.request_models import ChatRequest
from ..controllers.chat import chat_controller, ChatErrorType, ChatResult
from ..core.db_ops.agent_checkpoints_db import thread_exists


router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest, graph=Depends(get_app_graph)):
    result = await chat_controller(req.message, req.llm, graph, thread_id=None)

    if result.success:
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "ai_message": result.message,
                "thread_id": result.thread_id,
            },
        )
    else:
        return create_error_response(result)


@router.post("/chat/{thread_id}")
async def chat_thread(
    thread_id: str,
    req: ChatRequest,
    graph=Depends(get_app_graph),
    saver=Depends(get_graph_saver),
):
    thread_id = thread_id.strip()
    if not await thread_exists(saver, thread_id):
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
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "ai_message": result.message,
                "thread_id": result.thread_id,
            },
        )
    else:
        return create_error_response(result)


def create_error_response(result: ChatResult) -> JSONResponse:
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
