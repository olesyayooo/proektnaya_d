from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Query
from src.auth.dependencies import LibrarianDep
from src.common.schemas import ResponseSchema, PaginatedResponseSchema
from src.database import SessionDep
from src.loans.schemas import LoanHistoryOut, LoanStatus
from src.readers.dependencies import ReadersServiceDep
from src.readers.schemas import ReaderOut

readers_router = APIRouter(prefix="/readers", tags=["readers"])


@readers_router.get("", response_model=ResponseSchema[ReaderOut])
async def find_reader(
    reader_card: Annotated[int, Query(gt=0, le=9_223_372_036_854_775_807)],
    current_user: LibrarianDep,
    session: SessionDep,
    readers_service: ReadersServiceDep,
):
    return await readers_service.get_by_card(reader_card, session)


@readers_router.get("/{reader_id}/loans", response_model=PaginatedResponseSchema[list[LoanHistoryOut]])
async def get_reader_loans(
    reader_id: UUID,
    current_user: LibrarianDep,
    session: SessionDep,
    readers_service: ReadersServiceDep,
    loan_status: Annotated[LoanStatus | None, Query(alias="status")] = None,
    overdue: bool | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await readers_service.get_loans(reader_id, session, loan_status, skip, limit, overdue)
