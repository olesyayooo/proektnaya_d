from fastapi import APIRouter

from src.auth.router import auth_router

router = APIRouter()

router.include_router(auth_router)
from src.books.router import books_router

router.include_router(books_router)

from src.readers.router import readers_router
from src.loans.router import loans_router

router.include_router(readers_router)
router.include_router(loans_router)

from src.integration.router import integration_router

router.include_router(integration_router)
