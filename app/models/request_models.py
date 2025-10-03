from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    llm: str
    thread_id: str | None = None
