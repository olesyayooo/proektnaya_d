from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Query, status
from src.auth.dependencies import AuthDep, LibrarianDep
from src.common.schemas import PaginatedResponseSchema, ResponseSchema
from src.database import SessionDep
from src.loans.dependencies import LoansServiceDep
from src.loans.schemas import LoanHistoryOut, LoanStatus, LoanCreate

loans_router = APIRouter(prefix="/loans", tags=["loans"])


@loans_router.get("/me", response_model=PaginatedResponseSchema[list[LoanHistoryOut]])
async def get_my_loans(
    current_user: AuthDep,
    session: SessionDep,
    loans_service: LoansServiceDep,
    loan_status: Annotated[LoanStatus | None, Query(alias="status")] = None,
    overdue: bool | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await loans_service.get_reader_loans(current_user.id, session, loan_status, skip, limit, overdue)


@loans_router.post("", response_model=ResponseSchema[LoanHistoryOut], status_code=status.HTTP_201_CREATED)
async def issue_book(
    data: LoanCreate,
    current_user: LibrarianDep,
    session: SessionDep,
    loans_service: LoansServiceDep,
):
    return await loans_service.issue(data, current_user, session)


@loans_router.post("/{loan_id}/return", response_model=ResponseSchema[LoanHistoryOut])
async def return_book(
    loan_id: UUID,
    current_user: LibrarianDep,
    session: SessionDep,
    loans_service: LoansServiceDep,
):
    return await loans_service.return_book(loan_id, session)


@loans_router.get("", response_model=PaginatedResponseSchema[list[LoanHistoryOut]])
async def get_all_loans(
    current_user: LibrarianDep,
    session: SessionDep,
    loans_service: LoansServiceDep,
    loan_status: Annotated[LoanStatus | None, Query(alias="status")] = None,
    overdue: bool | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await loans_service.get_history(session, loan_status, overdue, skip, limit)
