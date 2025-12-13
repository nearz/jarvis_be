from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from .thread import Thread


class Project(BaseModel):
    title: str
    project_id: str
    created_at: datetime
    updated_at: datetime
