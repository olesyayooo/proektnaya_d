from fastapi import APIRouter

from src.auth.router import auth_router

router = APIRouter()

router.include_router(auth_router)
from src.books.router import books_router

router.include_router(books_router)
