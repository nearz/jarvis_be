from pydantic import BaseModel
from ..thread import Thread, ThreadMessage


class HistoryResponse(BaseModel):
    success: bool = True
    threads: list[Thread]


class ThreadHistoryResponse(BaseModel):
    success: bool = True
    messages: list[ThreadMessage]
