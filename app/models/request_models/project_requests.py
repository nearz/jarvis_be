from pydantic import BaseModel, Field


class ProjectRequest(BaseModel):
    title: str = Field(min_length=3)


class InstructionRequest(BaseModel):
    inst: str
