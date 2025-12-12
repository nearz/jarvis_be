from pydantic import BaseModel
from ..thread import Thread
from ..project import Project


class CreateProjectResponse(BaseModel):
    success: bool = True
    project_id: str


class ProjectResponse(BaseModel):
    success: bool = True
    instructions: str
    threads: list[Thread]


class ProjectsResponse(BaseModel):
    success: bool = True
    projects: list[Project]


class InstructionsResponse(BaseModel):
    success: bool = True
