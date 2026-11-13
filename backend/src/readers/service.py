from fastapi import HTTPException, status
from src.readers.repository import ReadersRepository
from src.readers.schemas import ReaderOut
from src.loans.service import LoansService


def require_reader(reader):
    if reader is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": "Читатель не найден",
                "error": "READER_NOT_FOUND"
            }
        )
    return reader


class ReadersService:
    def __init__(self, readers_repo: ReadersRepository, loans_service: LoansService):
        self.readers_repo = readers_repo
        self.loans_service = loans_service

    async def get_by_card(self, reader_card, session):
        reader = require_reader(await self.readers_repo.get_by_card(reader_card, session))
        return {"success": True, "data": ReaderOut.model_validate(reader)}

    async def get_loans(self, reader_id, session, loan_status, skip, limit, overdue=None):
        require_reader(await self.readers_repo.get_by_id(reader_id, session))
        return await self.loans_service.get_reader_loans(reader_id, session, loan_status, skip, limit, overdue)
