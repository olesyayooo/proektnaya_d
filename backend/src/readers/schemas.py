from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr


class ReaderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    email: EmailStr
    reader_card: int | None
