from uuid import uuid4

from ..models.project import Project
from ..models.controller_models import (
    CreateProjectResult,
    ProjectResult,
    ProjectsResult,
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
        project_id = str(uuid4())
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


# async def get_project_controller(project_id: str, app_db: AppDatabase) -> ProjectResult:
#     pass


# async def instructions_project_controller(
#     project_id: str, inst: str, user_id: str, app_db: AppDatabase
# ) -> InstructionsResponse:
#     pass
#
#
