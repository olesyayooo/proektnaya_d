from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Query
from src.auth.dependencies import OptionalAuthDep
from src.books.dependencies import BooksServiceDep
from src.books.schemas import BookOut, LibrarianBookOut
from src.common.schemas import ResponseSchema, PaginatedResponseSchema
from src.database import SessionDep

books_router = APIRouter(prefix="/books", tags=["books"])


@books_router.get("", response_model=PaginatedResponseSchema[list[BookOut]])
async def catalog(
    optional_user: OptionalAuthDep,
    session: SessionDep,
    books_service: BooksServiceDep,
    search: Annotated[str | None, Query(max_length=300)] = None,
    available: bool | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await books_service.catalog(session, search, available, skip, limit)


@books_router.get("/{book_id}", response_model=ResponseSchema[LibrarianBookOut | BookOut])
async def get_book(
    book_id: UUID,
    optional_user: OptionalAuthDep,
    session: SessionDep,
    books_service: BooksServiceDep,
):
    return await books_service.get_book(book_id, optional_user, session)
