from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    copy_id: UUID
    reader_id: UUID
    librarian_id: UUID
    issued_at: datetime
    due_date: date
    returned_at: datetime | None
