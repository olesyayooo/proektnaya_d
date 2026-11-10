from fastapi import HTTPException, status
from src.auth.schemas import UserRole
from src.books.repository import BooksRepository
from src.books.schemas import BookOut, LibrarianBookOut
from src.loans.repository import LoansRepository


def book_data(book, available):
    return {"id": book.id, "title": book.title, "author": book.author,
            "publication_year": book.publication_year, "publisher": book.publisher,
            "available": available}


class BooksService:
    def __init__(self, books_repo: BooksRepository, loans_repo: LoansRepository):
        self.books_repo = books_repo
        self.loans_repo = loans_repo

    async def catalog(self, session, search, available, skip, limit):
        rows, total = await self.books_repo.catalog(session, search, available, skip, limit)
        return {"success": True, "data": [BookOut(**book_data(*row)) for row in rows],
                "total": total, "skip": skip, "limit": limit}

    async def get_book(self, book_id, current_user, session):
        row = await self.books_repo.get_book(book_id, session)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "message": "Книга не найдена",
                    "error": "BOOK_NOT_FOUND"
                }
            )
        data = book_data(*row)
        if current_user.role == UserRole.librarian:
            loans = await self.loans_repo.get_active_for_book(book_id, session)
            book = LibrarianBookOut(**data, active_loans=loans)
        else:
            book = BookOut(**data)
        return {"success": True, "data": book}
