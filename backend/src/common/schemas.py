from pydantic import BaseModel, Field
from typing import Optional, TypeVar, Generic


T = TypeVar('T')

class ResponseSchema(BaseModel, Generic[T]):
    success: bool
    message: str | None = Field(default=None)
    data: Optional[T] = Field(default=None)
    error: str | None = Field(default=None)

class PaginatedResponseSchema(ResponseSchema, Generic[T]):
    total: int = Field(default=0, ge=0)
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1)
