from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class BooksModel(Base):
    __tablename__ = "books"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[str] = mapped_column(String(300))
    publication_year: Mapped[int] = mapped_column(Integer)
    publisher: Mapped[str] = mapped_column(String(300))


class BookCopiesModel(Base):
    __tablename__ = "book_copies"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id"), index=True)
