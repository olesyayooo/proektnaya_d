from sqlalchemy.orm import mapped_column, Mapped
from uuid import UUID
from sqlalchemy import String, Enum, BigInteger, UniqueConstraint
from uuid import uuid4

from src.database import Base
from src.auth.schemas import UserRole

class UsersModel(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("reader_card", name="uq_users_reader_card"),)
    reader_card: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role_enum", native_enum=False), server_default="reader", nullable=False, default=UserRole.reader)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255))
    