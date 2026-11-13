from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from secrets import compare_digest
from src.configs import settings
from src.integration.repository import IntegrationRepository
from src.integration.service import IntegrationService


def get_integration_repository():
    return IntegrationRepository()


def get_integration_service(
    integration_repo: IntegrationRepository = Depends(get_integration_repository),
):
    return IntegrationService(integration_repo)


IntegrationServiceDep = Annotated[IntegrationService, Depends(get_integration_service)]


integration_key_header = APIKeyHeader(name="X-Integration-Key", auto_error=False)


async def require_integration_key(
    api_key: Annotated[str | None, Depends(integration_key_header)],
):
    expected = settings.INTEGRATION_API_KEY
    if expected is None or not expected.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"success": False, "message": "Ключ интеграции не настроен",
                    "error": "INTEGRATION_NOT_CONFIGURED"}
        )
    if api_key is None or not compare_digest(api_key.encode(), expected.get_secret_value().encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Неверный или отсутствующий ключ интеграции",
                    "error": "INVALID_INTEGRATION_KEY"}
        )


IntegrationKeyDep = Annotated[None, Depends(require_integration_key)]
