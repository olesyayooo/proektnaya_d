from fastapi import APIRouter

from src.auth.router import auth_router

router = APIRouter()

router.include_router(auth_router)