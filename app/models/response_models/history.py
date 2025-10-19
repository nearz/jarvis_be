from pydantic import BaseModel
from ..thread import Thread, ThreadMessage


class HistoryResponse(BaseModel):
    threads: list[Thread]


class ThreadHistoryResponse(BaseModel):
    messages: list[ThreadMessage]
