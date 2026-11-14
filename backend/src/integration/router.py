from typing import Annotated
from fastapi import APIRouter, Query
from src.database import SessionDep
from src.common.schemas import ResponseSchema, PaginatedResponseSchema
from src.integration.dependencies import IntegrationServiceDep, IntegrationKeyDep
from src.integration.schemas import PurchaseImport, PurchaseImportOut, OverdueReportStatus
from src.loans.schemas import LoanHistoryOut

integration_router = APIRouter(prefix="/integration", tags=["integration"])


@integration_router.post("/purchases", response_model=ResponseSchema[PurchaseImportOut])
async def import_purchase(
    data: PurchaseImport,
    integration_key: IntegrationKeyDep,
    session: SessionDep,
    integration_service: IntegrationServiceDep,
):
    return await integration_service.import_purchase(data, session)


@integration_router.get("/overdue-report", response_model=PaginatedResponseSchema[list[LoanHistoryOut]])
async def get_overdue_report(
    integration_key: IntegrationKeyDep,
    session: SessionDep,
    integration_service: IntegrationServiceDep,
    report_status: Annotated[OverdueReportStatus, Query(alias="status")] = OverdueReportStatus.active,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
):
    return await integration_service.get_overdue_report(session, report_status, skip, limit)
