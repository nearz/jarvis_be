from pydantic import BaseModel, Field, field_validator

from datatime import datetime


# TODO: Can I verify that model value is correct form selection
class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    llm: str = Field(min_length=1)
    edited: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("message", "llm")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or only whitespace")
        return v.strip()
