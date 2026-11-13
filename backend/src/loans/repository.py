from sqlalchemy import select, func, case, exists, update, Date
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from src.books.models import BookCopiesModel, BooksModel
from src.loans.models import LoansModel
from src.auth.models import UsersModel
from src.auth.schemas import UserRole
from sqlalchemy.sql.functions import FunctionElement
from sqlalchemy.ext.compiler import compiles


class MoscowDate(FunctionElement):
    type = Date()
    inherit_cache = True


@compiles(MoscowDate, "postgresql")
def compile_moscow_date_pg(element, compiler, **kw):
    value = compiler.process(list(element.clauses)[0], **kw)
    return f"CAST(timezone('Europe/Moscow', {value}) AS DATE)"


@compiles(MoscowDate, "sqlite")
def compile_moscow_date_sqlite(element, compiler, **kw):
    value = compiler.process(list(element.clauses)[0], **kw)
    return f"date({value}, '+3 hours')"



class LoansRepository:
    async def get_active_for_book(self, book_id: UUID, session: AsyncSession):
        result = await session.execute(
            select(LoansModel, BooksModel, UsersModel)
            .join(BookCopiesModel, LoansModel.copy_id == BookCopiesModel.id)
            .join(BooksModel, BookCopiesModel.book_id == BooksModel.id)
            .join(UsersModel, LoansModel.reader_id == UsersModel.id)
            .where(BookCopiesModel.book_id == book_id, LoansModel.returned_at.is_(None))
            .order_by(LoansModel.issued_at, LoansModel.id)
        )
        return result.all()

    async def get_details(self, loan_id, session):
        result = await session.execute(
            select(LoansModel, BooksModel, UsersModel)
            .join(BookCopiesModel, LoansModel.copy_id == BookCopiesModel.id)
            .join(BooksModel, BookCopiesModel.book_id == BooksModel.id)
            .join(UsersModel, LoansModel.reader_id == UsersModel.id)
            .where(LoansModel.id == loan_id)
        )
        return result.one_or_none()

    async def get_history(self, session, loan_status, overdue, today, skip, limit, reader_id=None):
        status_expr = case((LoansModel.returned_at.is_not(None), "returned"), else_="active")
        end_date = case(
            (LoansModel.returned_at.is_not(None), MoscowDate(LoansModel.returned_at)),
            else_=today,
        )
        overdue_expr = end_date > LoansModel.due_date
        conditions = []
        if reader_id is not None:
            conditions.append(LoansModel.reader_id == reader_id)
        if loan_status is not None:
            conditions.append(status_expr == loan_status.value)
        if overdue is not None:
            conditions.append(overdue_expr if overdue else ~overdue_expr)
        total = await session.scalar(select(func.count()).select_from(LoansModel).where(*conditions))
        rows = await session.execute(
            select(LoansModel, BooksModel, UsersModel)
            .join(BookCopiesModel, LoansModel.copy_id == BookCopiesModel.id)
            .join(BooksModel, BookCopiesModel.book_id == BooksModel.id)
            .join(UsersModel, LoansModel.reader_id == UsersModel.id)
            .where(*conditions)
            .order_by(LoansModel.issued_at.desc(), LoansModel.id.desc())
            .offset(skip).limit(limit)
        )
        return rows.all(), total


    async def get_book(self, book_id, session):
        return await session.scalar(select(BooksModel).where(BooksModel.id == book_id))

    async def get_reader_by_card(self, reader_card, session):
        return await session.scalar(select(UsersModel).where(
            UsersModel.reader_card == reader_card, UsersModel.role == UserRole.reader
        ))

    async def get_free_copy(self, book_id, session):
        active_loan = exists(select(LoansModel.id).where(
            LoansModel.copy_id == BookCopiesModel.id, LoansModel.returned_at.is_(None)
        ))
        return await session.scalar(select(BookCopiesModel).where(
            BookCopiesModel.book_id == book_id, ~active_loan
        ).order_by(BookCopiesModel.id).limit(1).with_for_update(skip_locked=True))

    async def create(self, loan, session):
        session.add(loan)
        await session.flush()
        return loan

    async def mark_returned(self, loan_id, returned_at, session):
        # Conditional UPDATE makes two concurrent returns mutually exclusive.
        return await session.scalar(update(LoansModel).where(
            LoansModel.id == loan_id, LoansModel.returned_at.is_(None)
        ).values(returned_at=returned_at).returning(LoansModel))

    async def get_by_id(self, loan_id, session):
        return await session.scalar(select(LoansModel).where(LoansModel.id == loan_id))
