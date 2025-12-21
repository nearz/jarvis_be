from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..thread import Thread
from ..project import Project


class CreateProjectResponse(BaseModel):
    success: bool = True
    project_id: str


class DeleteProjectResponse(BaseModel):
    success: bool = True


class ProjectResponse(BaseModel):
    success: bool = True
    project_id: str
    title: str
    instructions: str
    created_at: datetime
    updated_at: datetime
    threads: Optional[list[Thread]] = []


class ProjectsResponse(BaseModel):
    success: bool = True
    projects: list[Project]


class UpdateProjectResponse(BaseModel):
    success: bool = True
    project_id: str
