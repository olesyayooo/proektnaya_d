from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class PurchasedBook(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=500)
    author: str = Field(min_length=1, max_length=300)
    publication_year: int = Field(ge=1, le=9999)
    publisher: str = Field(min_length=1, max_length=300)
    quantity: int = Field(ge=1, le=1000, strict=True)


class PurchaseImport(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    document_id: str = Field(min_length=1, max_length=200)
    books: list[PurchasedBook] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def limit_copies(self):
        if sum(book.quantity for book in self.books) > 5000:
            raise ValueError("Не более 5000 экземпляров в одном документе")
        return self


class ImportedBook(BaseModel):
    book_id: UUID
    quantity: int


class PurchaseImportOut(BaseModel):
    document_id: str
    already_imported: bool
    created_books: int
    created_copies: int
    books: list[ImportedBook]
