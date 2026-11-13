from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Annotated
from uuid import UUID

from src.auth.models import UsersModel
from src.database import SessionDep
from src.auth.jwt import decode_token
from src.auth.repository import AuthRepository
from src.auth.service import AuthService

security = HTTPBearer(auto_error=False)

async def get_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: SessionDep
):
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "Не выполнен вход в аккаунт",
                "error": "INVALID_TOKEN"
            }
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "Не выполнен вход в аккаунт",
                "error": "INVALID_TOKEN_STRUCTURE"
            }
        )

    try:
        user_uuid = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "Не выполнен вход в аккаунт",
                "error": "INVALID_ID_IN_TOKEN"
            }
        )

    repo = AuthRepository()
    user = await repo.get_by_id(user_uuid, session)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": "Аккаунт не найден",
                "error": "USER_NOT_FOUND"
            }
        )
    
    return user

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: SessionDep
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "Не выполнен вход в аккаунт",
                "error": "UNAUTHORIZED"
            }
        )
    current_user = await get_user(credentials, session)
    return current_user

async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: SessionDep
):
    if not credentials:
        return None
    try:
        optional_user = await get_user(credentials, session)
        return optional_user
    except HTTPException:
        return None


OptionalAuthDep = Annotated[UsersModel | None, Depends(get_optional_user)]

AuthDep = Annotated[UsersModel, Depends(get_current_user)]

def get_auth_repository():
    return AuthRepository()

def get_auth_service(
    auth_repo: AuthRepository = Depends(get_auth_repository)
):
    return AuthService(auth_repo)

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_librarian(current_user: AuthDep):
    from src.auth.schemas import UserRole
    if current_user.role != UserRole.librarian:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "Доступ разрешён только библиотекарю",
                "error": "LIBRARIAN_REQUIRED"
            }
        )
    return current_user


LibrarianDep = Annotated[UsersModel, Depends(get_librarian)]
