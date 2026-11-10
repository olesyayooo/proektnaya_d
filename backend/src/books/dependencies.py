from typing import Annotated
from fastapi import Depends
from src.books.repository import BooksRepository
from src.books.service import BooksService
from src.loans.dependencies import get_loans_repository
from src.loans.repository import LoansRepository


def get_books_repository():
    return BooksRepository()


def get_books_service(
    books_repo: BooksRepository = Depends(get_books_repository),
    loans_repo: LoansRepository = Depends(get_loans_repository),
):
    return BooksService(books_repo, loans_repo)


BooksServiceDep = Annotated[BooksService, Depends(get_books_service)]
