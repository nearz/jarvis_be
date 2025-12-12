from pydantic import BaseModel
from datetime import datetime


class Project(BaseModel):
    title: str
    project_id: str
    created_at: datetime
    updated_at: datetime
