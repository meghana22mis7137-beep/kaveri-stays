from typing import Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class ErrorDetail(BaseModel):
    status_code: int
    error: str
    code: str
    message: str
    details: Optional[dict] = None

class MessageResponse(BaseModel):
    message: str
    success: bool = True
