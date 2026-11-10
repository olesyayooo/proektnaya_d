from uuid import UUID
from pydantic import BaseModel
from src.loans.schemas import LoanOut


class BookOut(BaseModel):
    id: UUID
    title: str
    author: str
    publication_year: int
    publisher: str
    available: bool


class LibrarianBookOut(BookOut):
    active_loans: list[LoanOut]
