from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, DateTime, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class PurchaseImportModel(Base):
    __tablename__ = "purchase_imports"
    __table_args__ = (UniqueConstraint("document_id", name="uq_purchase_imports_document_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[str] = mapped_column(String(200))
    payload_hash: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
