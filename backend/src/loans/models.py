from datetime import datetime, date
from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, DateTime, Index, CheckConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class LoansModel(Base):
    __tablename__ = "loans"
    __table_args__ = (
        Index("uq_loans_active_copy", "copy_id", unique=True,
              postgresql_where=text("returned_at IS NULL"),
              sqlite_where=text("returned_at IS NULL")),
        CheckConstraint("due_date >= CAST(issued_at AS DATE)", name="ck_loans_due_date"),
        CheckConstraint("returned_at IS NULL OR returned_at >= issued_at", name="ck_loans_returned_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    copy_id: Mapped[UUID] = mapped_column(ForeignKey("book_copies.id"), index=True)
    reader_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    librarian_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    due_date: Mapped[date]
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
