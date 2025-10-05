from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from .dependencies import get_app_graph, get_graph_saver
from ..models.request_models import ChatRequest
from ..contollers.chat import chat_controller, ChatErrorType
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
        status_code = 400
        if result.error_type == ChatErrorType.VALIDATION_ERROR:
            status_code = 400
        elif result.error_type == ChatErrorType.GRAPH_EXECUTION_ERROR:
            status_code = 502
        elif result.error_type == ChatErrorType.RESPONSE_PROCESSING_ERROR:
            status_code = 502
        elif result.error_type == ChatErrorType.SYSTEM_ERROR:
            status_code = 500

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error_type": result.error_type.value if result.error_type else None,
                "error_details": result.error_details,
                "thread_id": result.thread_id,
            },
        )


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
                "error_type": ChatErrorType.VALIDATION_ERROR,
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
        status_code = 400
        if result.error_type == ChatErrorType.VALIDATION_ERROR:
            status_code = 400
        elif result.error_type == ChatErrorType.GRAPH_EXECUTION_ERROR:
            status_code = 502
        elif result.error_type == ChatErrorType.RESPONSE_PROCESSING_ERROR:
            status_code = 502
        elif result.error_type == ChatErrorType.SYSTEM_ERROR:
            status_code = 500

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error_type": result.error_type.value if result.error_type else None,
                "error_details": result.error_details,
                "thread_id": result.thread_id,
            },
        )
