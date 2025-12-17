from uuid import uuid4
from typing import Optional

from ..models.project import Project
from ..models.thread import Thread
from ..models.controller_models import (
    CreateProjectResult,
    ProjectResult,
    ProjectsResult,
    UpdateProjectResult,
    ErrorType,
)
from ..core.db_ops.app_db import AppDatabase, DatabaseException
from ..core.logging import get_logger

logger = get_logger(__name__)


async def create_project_controller(
    title: str, user_id: str, app_db: AppDatabase
) -> CreateProjectResult:
    try:
        logger.debug("title: %s, user_id: %s", title, user_id)
        project_id = "p-" + str(uuid4())
        project_db = await app_db.create_project(project_id, user_id, title)

        logger.info(
            "Project created | user_id: %s | project_id: %s", user_id, project_id
        )

        return CreateProjectResult(success=True, project_id=project_id)

    except DatabaseException as e:
        logger.exception("Database exception occurred | user_id: %s", user_id)
        return CreateProjectResult(
            success=False,
            error_type=ErrorType.DATABASE_ERROR,
            error_details="Database exception occurred",
        )

    except Exception as e:
        logger.exception("System error")
        return CreateProjectResult(
            success=False,
            error_type=ErrorType.SYSTEM_ERROR,
            error_details="Unexpected system failure",
        )


async def get_projects_controller(user_id: str, app_db: AppDatabase) -> ProjectsResult:
    try:
        projects_db = await app_db.get_user_projects(user_id)

        if projects_db is None:
            return ProjectsResult(success=True)

        projects = [
            Project(
                title=p["title"],
                project_id=p["id"],
                created_at=p["created_at"],
                updated_at=p["updated_at"],
            )
            for p in projects_db
        ]

        logger.info("Projects fetched | user_id: %s", user_id)

        return ProjectsResult(success=True, projects=projects)

    except DatabaseException as e:
        logger.exception("Database exception occurred | user_id: %s", user_id)
        return ProjectsResult(
            success=False,
            error_type=ErrorType.DATABASE_ERROR,
            error_details="Database exception occurred",
        )

    except Exception as e:
        logger.exception("System error")
        return ProjectsResult(
            success=False,
            error_type=ErrorType.SYSTEM_ERROR,
            error_details="Unexpected system failure",
        )


async def get_project_controller(
    project_id: str, app_db: AppDatabase, include_threads: bool
) -> ProjectResult:
    try:
        project_db = await app_db.get_project_by_id(project_id)
        project_threads_db = await app_db.get_project_threads(project_id)

        if project_db is None:
            # TODO: Handle error better
            return ProjectResult(success=False)

        project_res = ProjectResult(
            success=True,
            project_id=project_db["id"],
            title=project_db["title"],
            instructions=project_db["instructions"],
            created_at=project_db["created_at"],
            updated_at=project_db["updated_at"],
        )

        if project_threads_db is None or not include_threads:
            return project_res

        threads = [
            Thread(
                title=t["title"],
                thread_id=t["thread_id"],
                last_llm_used=t["last_llm_used"],
                created_at=t["created_at"],
                updated_at=t["updated_at"],
            )
            for t in project_threads_db
        ]
        project_res.threads = threads

        return project_res

    except DatabaseException as e:
        logger.exception("Database exception occurred | project_id: %s", project_id)
        return ProjectResult(
            success=False,
            error_type=ErrorType.DATABASE_ERROR,
            error_details="Database exception occurred",
        )

    except Exception as e:
        logger.exception("System error")
        return ProjectResult(
            success=False,
            error_type=ErrorType.SYSTEM_ERROR,
            error_details="Unexpected system failure",
        )


async def update_project_controller(
    project_id: str,
    user_id: str,
    app_db: AppDatabase,
    title: Optional[str] = None,
    inst: Optional[str] = None,
) -> UpdateProjectResult:

    try:
        await app_db.update_project(project_id, title=title, instructions=inst)
        return UpdateProjectResult(success=True)

    except DatabaseException as e:
        logger.exception("Database exception occurred | user_id: %s", user_id)
        return UpdateProjectResult(
            success=False,
            error_type=ErrorType.DATABASE_ERROR,
            error_details="Database exception occurred",
        )

    except Exception as e:
        logger.exception("System error")
        return UpdateProjectResult(
            success=False,
            error_type=ErrorType.SYSTEM_ERROR,
            error_details="Unexpected system failure",
        )
