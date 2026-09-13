from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    request_id: Optional[str] = None


class APIErrorDetails(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class APIErrorResponse(BaseModel):
    success: bool = False
    error: APIErrorDetails
    request_id: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
