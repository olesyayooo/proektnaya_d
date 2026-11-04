from fastapi import APIRouter, status

from src.auth.schemas import UserRegister, UserLogin, UserOutMe, UserUpdateMe
from src.database import SessionDep
from src.auth.dependencies import AuthServiceDep, AuthDep
from src.common.schemas import ResponseSchema

auth_router = APIRouter(prefix="/auth", tags=["authentication"])

@auth_router.post("/register", response_model=ResponseSchema, status_code=status.HTTP_201_CREATED)
async def register_user(
    user: UserRegister,
    session: SessionDep,
    auth_service: AuthServiceDep
):
    register_data = await auth_service.register_user(user, session)
    return register_data


@auth_router.post("/login", response_model=ResponseSchema, status_code=status.HTTP_200_OK)
async def login_user(
    user: UserLogin,
    session: SessionDep,
    auth_service: AuthServiceDep
):
    login_data = await auth_service.login_user(user, session)
    return login_data

@auth_router.get("/me", response_model=ResponseSchema[UserOutMe], status_code=status.HTTP_200_OK)
async def get_me(
    current_user: AuthDep
):
    return {
        "success": True,
        "data": current_user
    }

@auth_router.patch("/me", response_model=ResponseSchema[UserOutMe], status_code=status.HTTP_200_OK)
async def update_me(
    update_data: UserUpdateMe,
    current_user: AuthDep,
    session: SessionDep,
    auth_service: AuthServiceDep
):
    updated_user = await auth_service.update_me(update_data, current_user, session)
    return updated_user