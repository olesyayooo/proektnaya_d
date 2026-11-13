from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.models import UsersModel
from src.auth.schemas import UserRole


class ReadersRepository:
    async def get_by_card(self, reader_card: int, session: AsyncSession):
        return await session.scalar(select(UsersModel).where(
            UsersModel.reader_card == reader_card, UsersModel.role == UserRole.reader
        ))

    async def get_by_id(self, reader_id: UUID, session: AsyncSession):
        return await session.scalar(select(UsersModel).where(
            UsersModel.id == reader_id, UsersModel.role == UserRole.reader
        ))
