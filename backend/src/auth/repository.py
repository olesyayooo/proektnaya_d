from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID

from src.auth.models import UsersModel

class AuthRepository:
    async def register_user(self, user: UsersModel, session: AsyncSession):
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    
    async def get_by_email(self, email: str, session: AsyncSession):
        query = select(UsersModel).where(UsersModel.email == email)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        return user
    
    async def get_by_id(self, id: UUID, session: AsyncSession):
        query = select(UsersModel).where(UsersModel.id == id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        return user