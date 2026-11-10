from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from src.books.models import BookCopiesModel
from src.loans.models import LoansModel


class LoansRepository:
    async def get_active_for_book(self, book_id: UUID, session: AsyncSession):
        result = await session.scalars(
            select(LoansModel).join(BookCopiesModel, LoansModel.copy_id == BookCopiesModel.id)
            .where(BookCopiesModel.book_id == book_id, LoansModel.returned_at.is_(None))
            .order_by(LoansModel.issued_at, LoansModel.id)
        )
        return result.all()
