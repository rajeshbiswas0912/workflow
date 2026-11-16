from pydantic import BaseModel, Field, AfterValidator
from datetime import datetime, timezone
from typing import Annotated, Generic, TypeVar
from math import ceil

T = TypeVar("T")

def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

UTCDateTime = Annotated[datetime, AfterValidator(_as_utc)]


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str = "Success"

class ErrorResponse(BaseModel):
    success: bool = False
    data: dict = Field(default_factory=dict)
    message: str

class Pagination(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def build(cls, *, page: int, page_size: int, total_items: int) -> "Pagination":
        total_pages = ceil(total_items / page_size) if total_items else 0
        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

class Page(BaseModel, Generic[T]):
    items: list[T]
    pagination: Pagination
