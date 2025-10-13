from pydantic import BaseModel
from typing import Optional


class SuccessResponse(BaseModel):
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error_type: Optional[str] = None
    error_details: Optional[str] = None
