from datetime import date, datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    copy_id: UUID
    reader_id: UUID
    librarian_id: UUID
    issued_at: datetime
    due_date: date
    returned_at: datetime | None


class LoanStatus(str, Enum):
    active = "active"
    returned = "returned"


class LoanBookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    author: str
    publication_year: int
    publisher: str


class LoanReaderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    reader_card: int | None


class LoanHistoryOut(LoanOut):
    status: LoanStatus
    book: LoanBookOut
    reader: LoanReaderOut
    overdue: bool
    overdue_days: int = Field(ge=0)


class LoanCreate(BaseModel):
    book_id: UUID
    reader_card: int = Field(gt=0, le=9_223_372_036_854_775_807)
    due_date: date
