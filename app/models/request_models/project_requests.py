from pydantic import BaseModel, Field
from typing import Optional


class ProjectRequest(BaseModel):
    title: str = Field(min_length=3)


class UpdateProjectRequest(BaseModel):
    title: Optional[str] = None
    instructions: Optional[str] = None
