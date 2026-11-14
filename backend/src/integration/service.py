import hashlib
import json
from fastapi import HTTPException, status
from src.integration.repository import IntegrationRepository
from src.integration.schemas import PurchaseImportOut, OverdueReportStatus
from src.loans.service import LoansService
from src.loans.schemas import LoanStatus


class IntegrationService:
    def __init__(self, integration_repo: IntegrationRepository, loans_service: LoansService):
        self.integration_repo = integration_repo
        self.loans_service = loans_service

    async def import_purchase(self, data, session):
        # Normalize line order and combine duplicate positions for retry comparison.
        positions = {}
        for item in data.books:
            key = (item.title, item.author, item.publication_year, item.publisher)
            positions[key] = positions.get(key, 0) + item.quantity
        canonical = sorted((*key, quantity) for key, quantity in positions.items())
        payload_hash = hashlib.sha256(json.dumps(canonical, ensure_ascii=False).encode()).hexdigest()
        try:
            await self.integration_repo.lock_imports(session)
            previous = await self.integration_repo.get_document(data.document_id, session)
            if previous is not None:
                if previous.payload_hash != payload_hash:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={"success": False, "message": "Документ уже загружен с другими данными",
                                "error": "PURCHASE_DOCUMENT_CONFLICT"}
                    )
                result = PurchaseImportOut(**previous.result)
                result.already_imported = True
                await session.commit()
                return {"success": True, "data": result}
            created_books = 0
            imported = []
            # One result position per edition, even if the document repeats a line.
            for key, quantity in sorted(positions.items()):
                item = next(item for item in data.books if
                            (item.title, item.author, item.publication_year, item.publisher) == key)
                book = await self.integration_repo.find_book(item, session)
                if book is None:
                    book = await self.integration_repo.create_book(item, session)
                    created_books += 1
                await self.integration_repo.add_copies(book.id, quantity, session)
                imported.append({"book_id": book.id, "quantity": quantity})
            result = PurchaseImportOut(
                document_id=data.document_id, already_imported=False,
                created_books=created_books, created_copies=sum(positions.values()), books=imported
            )
            await self.integration_repo.save_document(
                data.document_id, payload_hash, result.model_dump(mode="json"), session
            )
            await session.commit()
            return {"success": True, "data": result}
        except Exception:
            await session.rollback()
            raise


    async def get_overdue_report(self, session, report_status, skip, limit):
        loan_status = None if report_status == OverdueReportStatus.all else LoanStatus(report_status.value)
        return await self.loans_service.get_history(
            session, loan_status=loan_status, overdue=True, skip=skip, limit=limit
        )
