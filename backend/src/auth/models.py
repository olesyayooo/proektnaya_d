from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String, Enum
from uuid import uuid4

from src.database import Base
from src.auth.schemas import UserRole

class UsersModel(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    role: Mapped[Enum] = mapped_column(Enum(UserRole, name="user_role_enum", native_enum=False), server_default="reader", nullable=False, default=UserRole.reader)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255))
    