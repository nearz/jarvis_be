from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime

from ..token import Token
from ..thread import Thread, ThreadMessage
from ..project import Project
from ..model import Model


class ErrorType(Enum):
    AUTHORIZATION_ERROR = "authorization_error"
    FORBIDDEN_ERROR = "forbidden_error"
    VALIDATION_ERROR = "validation_error"
    DATABASE_ERROR = "database_error"
    LLM_ERROR = "llm_error"
    GRAPH_EXECUTION_ERROR = "graph_execution_error"
    LLM_RESPONSE_PROCESSING_ERROR = "response_processing_error"
    SYSTEM_ERROR = "system_error"


@dataclass
class BaseResult:
    success: bool
    error_type: Optional[ErrorType] = None
    error_details: Optional[str] = None


@dataclass
class SupportModelsResult(BaseResult):
    supported_models: Optional[list[Model]] = None


@dataclass
class AuthResult(BaseResult):
    token: Optional[Token] = None


@dataclass
class HistoryResult(BaseResult):
    threads: Optional[list[Thread]] = None


@dataclass
class ThreadMessagesResult(BaseResult):
    messages: Optional[list[ThreadMessage]] = None


@dataclass
class ThreadDeleteResult(BaseResult):
    pass


@dataclass
class CreateProjectResult(BaseResult):
    project_id: Optional[str] = None


@dataclass
class ProjectResult(BaseResult):
    project_id: Optional[str] = None
    title: Optional[str] = None
    instructions: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    threads: Optional[list[Thread]] = None


@dataclass
class ProjectsResult(BaseResult):
    projects: Optional[list[Project]] = None


@dataclass
class UpdateProjectResult(BaseResult):
    pass


@dataclass
class ContentStreamChunk:
    type: str = "content"
    text: str = ""


@dataclass
class DoneStreamChunk:
    type: str = "done"
    thread_id: str = ""


@dataclass
class ErrorStreamChunk:
    type: str = "error"
    message: str = ""
