from pydantic import BaseModel
from datetime import datetime


class Thread(BaseModel):
    title: str
    thread_id: str
    created_at: datetime
    updated_at: datetime


class ThreadMessage(BaseModel):
    index: int
    content: str
    message_type: str
    message_id: str
    thread_id: str
    created_at: datetime
