import json
from dataclasses import asdict
from typing import Union
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from .dependencies import (
    get_app_graph,
    get_graph_saver,
    get_current_user,
    get_app_db,
    thread_validation,
)
from ..agent.state import AgentState, ContextSchema
from ..models.request_models import ChatRequest
from ..models import User
from ..controllers.chat import chat_controller
from ..core.db_ops.app_db import AppDatabase
from ..core.logging import get_logger
from .errors import create_error_response


logger = get_logger(__name__)
router = APIRouter()


@router.post("/chat")
async def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
    saver: AsyncSqliteSaver = Depends(get_graph_saver),
    graph=Depends(get_app_graph),
):
    logger.info("New chat | message len: %d | llm: %s", len(req.message), req.llm)
    return StreamingResponse(
        _event_generator(req.message, req.llm, user.id, app_db, saver, graph, None),
        media_type="text/event-stream",
    )


@router.post("/chat/{thread_id}")
async def chat_thread(
    req: ChatRequest,
    thread_id: str = Depends(thread_validation),
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
    saver: AsyncSqliteSaver = Depends(get_graph_saver),
    graph=Depends(get_app_graph),
):
    thread_id = thread_id.strip()
    logger.info("Chat thread request | thread_id: %s", thread_id)

    return StreamingResponse(
        _event_generator(
            req.message, req.llm, user.id, app_db, saver, graph, thread_id
        ),
        media_type="text/event-stream",
    )


async def _event_generator(
    message: str,
    llm: str,
    user_id: str,
    app_db: AppDatabase,
    saver: AsyncSqliteSaver,
    graph: CompiledStateGraph[AgentState, ContextSchema, AgentState, AgentState],
    thread_id: Union[str, None],
):
    logger.info(
        "Starting event generator | thread_id: %s | user_id: %s", thread_id, user_id
    )
    async for chunk in chat_controller(
        message,
        llm,
        user_id,
        app_db,
        saver,
        graph,
        thread_id=thread_id,
        project_id=None,
    ):
        try:
            data = json.dumps(asdict(chunk))
            yield f"data: {data}\n\n"
        except Exception as e:
            logger.exception(
                "Exception occured while streaming | thread_id: %s | user_id: %s",
                thread_id,
                user_id,
            )
            err_data = json.dumps(
                {"type": "error", "message": "Unexpected system error"}
            )
            yield f"data: {err_data}\n\n"
            break
