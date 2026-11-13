from uuid import UUID
from pydantic import BaseModel
from src.loans.schemas import LoanHistoryOut


class BookOut(BaseModel):
    id: UUID
    title: str
    author: str
    publication_year: int
    publisher: str
    available: bool


class LibrarianBookOut(BookOut):
    active_loans: list[LoanHistoryOut]
