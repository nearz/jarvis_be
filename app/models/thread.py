from pydantic import BaseModel
from datetime import datetime


class Thread(BaseModel):
    title: str
    thread_id: str
    created_at: datetime
    updated_at: datetime
