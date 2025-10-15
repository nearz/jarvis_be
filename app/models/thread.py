from pydantic import BaseModel


class Thread(BaseModel):
    title: str
    thread_id: str
