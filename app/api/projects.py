import json
from dataclasses import asdict
from typing import Union
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from .dependencies import (
    get_current_user,
    get_app_db,
    project_validation,
    thread_validation,
    get_graph_saver,
    get_app_graph,
)
from ..controllers.projects import (
    create_project_controller,
    get_projects_controller,
    update_project_controller,
    get_project_controller,
)
from ..controllers.chat import chat_controller
from ..agent.state import AgentState, ContextSchema
from ..models import User
from ..models.request_models import (
    ProjectRequest,
    ChatRequest,
    UpdateProjectRequest,
)
from ..models.response_models import (
    CreateProjectResponse,
    ProjectsResponse,
    UpdateProjectResponse,
    ProjectResponse,
)
from ..core.db_ops.app_db import AppDatabase
from ..core.logging import get_logger
from .errors import create_error_response


logger = get_logger(__name__)
router = APIRouter()


@router.get("/projects")
async def get_projects(
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
):
    logger.info("Get projects request | user_id: %s", user.id)
    result = await get_projects_controller(user.id, app_db)

    if not result.success:
        logger.warning("Project fetch failure | user_id: %s", user.id)
        return create_error_response(result)

    logger.info("Project successfully fetched | user_id: %s", user.id)
    if result.projects:
        return ProjectsResponse(projects=result.projects)
    else:
        logger.info("No project history | user_id: %s", user.id)
        return ProjectsResponse(projects=[])


@router.post("/projects")
async def create_project(
    req: ProjectRequest,
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
):

    logger.info("Create project request | user_id: %s", user.id)
    result = await create_project_controller(req.title, user.id, app_db)

    if not result.success or result.project_id is None:
        logger.warning("Project creation failure | user_id: %s", user.id)
        return create_error_response(result)

    logger.info("Project successfully created | user_id: %s", user.id)

    return CreateProjectResponse(project_id=result.project_id)


@router.post("/projects/{project_id}")
async def update_project(
    req: UpdateProjectRequest,
    project_id: str = Depends(project_validation),
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
):
    logger.info(
        "Update project instructions request | user_id: %s | project_id: %s",
        user.id,
        project_id,
    )
    result = await update_project_controller(
        project_id, user.id, app_db, req.title, req.instructions
    )

    if not result.success:
        logger.warning(
            "Project creation failure | user_id: %s | project_id: %s",
            user.id,
            project_id,
        )
        return create_error_response(result)

    logger.info(
        "Project successfully updated | user_id: %s | project_id: %s",
        user.id,
        project_id,
    )
    return UpdateProjectResponse(project_id=project_id)

    """
    Returns:
    Boolean? - updated succesfully
    """
    pass


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str = Depends(project_validation),
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
):
    logger.info(
        "Get project request | user_id: %s | project_id: %s",
        user.id,
        project_id,
    )
    result = await get_project_controller(project_id, app_db)

    if not result.success:
        logger.warning(
            "Get project failure | user_id: %s | project_id: %s",
            user.id,
            project_id,
        )
        return create_error_response(result)

    logger.info(
        "Get project success | user_id: %s | project_id: %s",
        user.id,
        project_id,
    )

    if any(
        p is None
        for p in (
            result.title,
            result.instructions,
            result.created_at,
            result.updated_at,
        )
    ):
        raise HTTPException(status_code=500, detail="Unexpected missing messages")

    project_resp = ProjectResponse(
        project_id=result.project_id,
        title=result.title,
        instructions=result.instructions,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )
    if result.threads is None:
        project_resp.threads = []
        return project_resp
    else:
        project_resp.threads = result.threads
        return project_resp


@router.post("/projects/{project_id}/chat")
async def project_new_chat(
    req: ChatRequest,
    project_id: str = Depends(project_validation),
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
    saver: AsyncSqliteSaver = Depends(get_graph_saver),
    graph=Depends(get_app_graph),
):
    logger.info(
        "New project chat | project_id: %s | user_id: %s | llm: %s",
        project_id,
        user.id,
        req.llm,
    )
    return StreamingResponse(
        _event_generator(
            project_id,
            req.message,
            req.llm,
            user.id,
            app_db,
            saver,
            graph,
            thread_id=None,
        ),
        media_type="text/event-stream",
    )


@router.post("/projects/{project_id}/chat/{thread_id}")
async def project_chat(
    req: ChatRequest,
    project_id: str = Depends(project_validation),
    thead_id: str = Depends(thread_validation),
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
    saver: AsyncSqliteSaver = Depends(get_graph_saver),
    graph=Depends(get_app_graph),
):
    logger.info(
        "Project chat | project_id: %s | user_id: %s | llm: %s",
        project_id,
        user.id,
        req.llm,
    )
    return StreamingResponse(
        _event_generator(
            project_id,
            req.message,
            req.llm,
            user.id,
            app_db,
            saver,
            graph,
            thread_id=thead_id,
        ),
        media_type="text/event-stream",
    )


async def _event_generator(
    project_id: str,
    message: str,
    llm: str,
    user_id: str,
    app_db: AppDatabase,
    saver: AsyncSqliteSaver,
    graph: CompiledStateGraph[AgentState, ContextSchema, AgentState, AgentState],
    *,
    thread_id: Union[str, None],
):
    logger.info(
        "Starting event generator | project_id: %s | thread_id: %s | user_id: %s",
        project_id,
        thread_id,
        user_id,
    )
    async for chunk in chat_controller(
        message,
        llm,
        user_id,
        app_db,
        saver,
        graph,
        thread_id=thread_id,
        project_id=project_id,
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
