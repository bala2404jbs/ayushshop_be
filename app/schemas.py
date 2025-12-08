from typing import List, Generic, TypeVar
from sqlmodel import SQLModel

T = TypeVar("T")

class PaginatedResponse(SQLModel, Generic[T]):
    data: List[T]
    page: int
    pageSize: int
    totalItem: int
    totalPage: int
