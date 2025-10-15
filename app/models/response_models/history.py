from pydantic import BaseModel
from ..thread import Thread


class HistoryResponse(BaseModel):
    threads: list[Thread]
