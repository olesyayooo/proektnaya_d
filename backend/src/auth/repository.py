from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from secrets import randbelow
from uuid import UUID

from src.auth.models import UsersModel

class AuthRepository:
    async def register_user(self, user: UsersModel, session: AsyncSession):
        # The unique constraint is the authority, including concurrent registrations.
        for _ in range(20):
            user.reader_card = randbelow(9_000_000_000) + 1_000_000_000
            session.add(user)
            try:
                await session.commit()
                await session.refresh(user)
                return user
            except IntegrityError as exc:
                await session.rollback()
                original = exc.orig
                cause = getattr(original, "__cause__", None)
                constraint = (
                    getattr(getattr(original, "diag", None), "constraint_name", None)
                    or getattr(original, "constraint_name", None)
                    or getattr(cause, "constraint_name", None)
                )
                if constraint != "uq_users_reader_card":
                    raise
        raise RuntimeError("Could not allocate a unique reader card")

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