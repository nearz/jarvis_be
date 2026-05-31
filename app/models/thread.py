from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Thread(BaseModel):
    title: str
    thread_id: str
    last_llm_used: str
    created_at: datetime
    updated_at: datetime


class ThreadMessage(BaseModel):
    index: int
    content: str
    llm: str
    message_type: str
    message_id: str
    thread_id: str
    created_at: datetime
    attached_context: Optional[str] = None
