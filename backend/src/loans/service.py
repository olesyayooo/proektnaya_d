from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from src.loans.models import LoansModel
from zoneinfo import ZoneInfo
from src.loans.repository import LoansRepository
from src.loans.schemas import LoanOut, LoanBookOut, LoanHistoryOut, LoanReaderOut, LoanStatus


def loan_details(loan, book, reader, today=None):
    today = today or datetime.now(ZoneInfo("Europe/Moscow")).date()
    end_date = today
    if loan.returned_at is not None:
        returned_at = loan.returned_at
        if returned_at.tzinfo is None:
            returned_at = returned_at.replace(tzinfo=timezone.utc)
        end_date = returned_at.astimezone(ZoneInfo("Europe/Moscow")).date()
    overdue_days = max(0, (end_date - loan.due_date).days)
    return LoanHistoryOut(
        **LoanOut.model_validate(loan).model_dump(),
        status=LoanStatus.returned if loan.returned_at is not None else LoanStatus.active,
        overdue=overdue_days > 0, overdue_days=overdue_days,
        book=LoanBookOut.model_validate(book), reader=LoanReaderOut.model_validate(reader)
    )


class LoansService:
    def __init__(self, loans_repo: LoansRepository):
        self.loans_repo = loans_repo

    async def get_reader_loans(self, reader_id, session, loan_status, skip, limit, overdue=None):
        return await self.get_history(session, loan_status, overdue, skip, limit, reader_id)

    async def get_history(self, session, loan_status, overdue, skip, limit, reader_id=None):
        today = datetime.now(ZoneInfo("Europe/Moscow")).date()
        rows, total = await self.loans_repo.get_history(
            session, loan_status, overdue, today, skip, limit, reader_id
        )
        data = [loan_details(loan, book, reader, today) for loan, book, reader in rows]
        return {"success": True, "data": data, "total": total, "skip": skip, "limit": limit}


    async def issue(self, data, current_user, session):
        issued_at = datetime.now(timezone.utc)
        today = issued_at.astimezone(ZoneInfo("Europe/Moscow")).date()
        if data.due_date < today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Срок возврата не может быть в прошлом",
                        "error": "INVALID_DUE_DATE"}
            )
        book = await self.loans_repo.get_book(data.book_id, session)
        if book is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Книга не найдена", "error": "BOOK_NOT_FOUND"}
            )
        reader = await self.loans_repo.get_reader_by_card(data.reader_card, session)
        if reader is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Читатель не найден", "error": "READER_NOT_FOUND"}
            )
        copy = await self.loans_repo.get_free_copy(data.book_id, session)
        if copy is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"success": False, "message": "Нет свободных экземпляров книги",
                        "error": "NO_AVAILABLE_COPIES"}
            )
        loan = LoansModel(copy_id=copy.id, reader_id=reader.id, librarian_id=current_user.id,
                          issued_at=issued_at, due_date=data.due_date, returned_at=None)
        try:
            await self.loans_repo.create(loan, session)
            result = loan_details(loan, book, reader)
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            original = exc.orig
            constraint = (getattr(getattr(original, "diag", None), "constraint_name", None)
                          or getattr(original, "constraint_name", None)
                          or getattr(getattr(original, "__cause__", None), "constraint_name", None))
            if constraint != "uq_loans_active_copy":
                raise
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"success": False, "message": "Экземпляр уже выдан, повторите попытку",
                        "error": "COPY_ALREADY_LOANED"}
            ) from exc
        return {"success": True, "data": result}

    async def return_book(self, loan_id, session):
        loan = await self.loans_repo.mark_returned(loan_id, datetime.now(timezone.utc), session)
        if loan is None:
            existing = await self.loans_repo.get_by_id(loan_id, session)
            if existing is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"success": False, "message": "Выдача не найдена", "error": "LOAN_NOT_FOUND"}
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"success": False, "message": "Книга уже возвращена", "error": "LOAN_ALREADY_RETURNED"}
            )
        details = await self.loans_repo.get_details(loan_id, session)
        result = loan_details(*details)
        await session.commit()
        return {"success": True, "data": result}
