from fastapi import APIRouter, Depends


from .dependencies import get_current_user, get_app_db
from ..controllers.projects import (
    create_project_controller,
    get_projects_controller,
)
from ..models import User
from ..models.request_models import (
    ProjectRequest,
    ChatRequest,
    InstructionRequest,
)
from ..models.response_models import CreateProjectResponse, ProjectsResponse
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
    # NOTE: Need a project_validation dependency similar to thread_validation
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

    """
    Returns:
    Projects - list of projects
    """
    pass


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


@router.post("/projects/{project_id}/instructions")
async def update_instructions(
    req: InstructionRequest,
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
):
    # NOTE: Need a project_validation dependency similar to thread_validation
    """
    Returns:
    Boolean? - updated succesfully
    """
    pass


@router.get("/projects/{project_id}")
async def get_project(
    user: User = Depends(get_current_user),
    app_db: AppDatabase = Depends(get_app_db),
):
    # NOTE: Need a project_validation dependency similar to thread_validation
    """
    Returns:
    Project ID
    Project Instructions
    List of Threads
    """
    pass


# NOTE: I think the below will not be endpoints. Thread requests
# Will still go through chat endpoint, just with a project_id
# if thread is part of a project.
# @router.get("/projects/{project_id}/threads")
# async def new_project_thread(
#     req: ChatRequest,
#     user: User = Depends(get_current_user),
#     app_db: AppDatabase = Depends(get_app_db),
# ):
#     """
#     ChatRequest - for new thread under project
#     """
#     pass
#
#
# @router.post("/projects/{project_id}/threads/{thread_id}")
# async def project_thread(
#     req: ChatRequest,
#     user: User = Depends(get_current_user),
#     app_db: AppDatabase = Depends(get_app_db),
# ):
#     """
#     ChatRequest - for message to existing thread
#     """
#     pass
