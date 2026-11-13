from fastapi import APIRouter
from src.database import SessionDep
from src.common.schemas import ResponseSchema
from src.integration.dependencies import IntegrationServiceDep, IntegrationKeyDep
from src.integration.schemas import PurchaseImport, PurchaseImportOut

integration_router = APIRouter(prefix="/integration", tags=["integration"])


@integration_router.post("/purchases", response_model=ResponseSchema[PurchaseImportOut])
async def import_purchase(
    data: PurchaseImport,
    integration_key: IntegrationKeyDep,
    session: SessionDep,
    integration_service: IntegrationServiceDep,
):
    return await integration_service.import_purchase(data, session)
