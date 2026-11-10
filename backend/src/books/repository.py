import re
from uuid import UUID
from sqlalchemy import select, exists, func, case, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.books.models import BooksModel, BookCopiesModel
from src.loans.models import LoansModel


def book_available():
    active_loan = exists(select(LoansModel.id).where(
        LoansModel.copy_id == BookCopiesModel.id, LoansModel.returned_at.is_(None)
    )).correlate(BookCopiesModel)
    return exists(select(BookCopiesModel.id).where(
        BookCopiesModel.book_id == BooksModel.id, ~active_loan
    )).correlate(BooksModel)


class BooksRepository:
    async def catalog(self, session: AsyncSession, search: str | None,
                      available: bool | None, skip: int, limit: int):
        availability = book_available()
        conditions = []
        tokens = re.findall(r"\w+", (search or "").lower(), flags=re.UNICODE)
        for token in tokens:
            conditions.append(or_(
                BooksModel.title.icontains(token, autoescape=True),
                BooksModel.author.icontains(token, autoescape=True),
            ))
        if available is not None:
            conditions.append(availability if available else ~availability)
        total = await session.scalar(select(func.count()).select_from(BooksModel).where(*conditions))
        query = select(BooksModel, availability.label("available")).where(*conditions)
        if tokens:
            phrase = " ".join(tokens)
            query = query.order_by(case(
                (func.lower(BooksModel.title) == phrase, 0),
                (func.lower(BooksModel.author) == phrase, 1),
                else_=2,
            ))
        result = await session.execute(query.order_by(BooksModel.title, BooksModel.id).offset(skip).limit(limit))
        return result.all(), total

    async def get_book(self, book_id: UUID, session: AsyncSession):
        result = await session.execute(select(BooksModel, book_available().label("available"))
                                       .where(BooksModel.id == book_id))
        return result.one_or_none()
