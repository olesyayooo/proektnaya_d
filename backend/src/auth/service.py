from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from src.auth.models import UsersModel
from src.auth.schemas import UserRegister, UserLogin, UserUpdateMe
from src.auth.security import hash_password, verify_password
from src.auth.repository import AuthRepository
from src.auth.jwt import create_token

class AuthService:
    def __init__(self, auth_repo: AuthRepository):
        self.auth_repo = auth_repo

    async def register_user(self, user: UserRegister, session: AsyncSession):
        if user.password != user.password_confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "Пароль не совпадает",
                    "error": "PASSWORDS_DO_NOT_MATCH"
                }
            )
        existing_email = await self.auth_repo.get_by_email(user.email, session)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": "Email занят",
                    "error": "EMAIL_IN_USE"
                }
            )
        user_dict = user.model_dump(exclude={"password", "password_confirm"})
        user_dict["hashed_password"] = hash_password(user.password)
        user = UsersModel(**user_dict)
        await self.auth_repo.register_user(user, session)
        return {
            "success": True,
            "message": "Регистрация прошла успешно! Войдите в аккаунт."
        }

    async def login_user(self, user: UserLogin, session: AsyncSession):
        existing_user = await self.auth_repo.get_by_email(user.email, session)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "message": "Неверный email или пароль",
                    "error": "WRONG_EMAIL_OR_PASSWORD"
                }
            )
        if not verify_password(user.password, existing_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "message": "Неверный email или пароль",
                    "error": "WRONG_EMAIL_OR_PASSWORD"
                }
            )
        token = create_token({"sub": str(existing_user.id)})
        return {
            "success": True,
            "data": {
                "token": token,
                "token_type": "bearer",
                "user_id": str(existing_user.id)
            }
        }
    
    async def update_me(self, update_data: UserUpdateMe, current_user: UsersModel, session: AsyncSession):
        update_dict = update_data.model_dump(exclude_unset=True)
        for k, v in update_dict.items():
            setattr(current_user, k, v)
        await session.commit()
        return {
            "success": True,
            "data": current_user
        }