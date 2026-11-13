from sqlalchemy import select, text
from src.books.models import BooksModel, BookCopiesModel
from src.integration.models import PurchaseImportModel


class IntegrationRepository:
    async def lock_imports(self, session):
        # Serialize local imports, also preventing duplicate catalog rows from
        # different purchase documents arriving concurrently.
        if session.get_bind().dialect.name == "postgresql":
            await session.execute(text("SELECT pg_advisory_xact_lock(847231901)"))

    async def get_document(self, document_id, session):
        return await session.scalar(select(PurchaseImportModel).where(
            PurchaseImportModel.document_id == document_id
        ))

    async def find_book(self, data, session):
        return await session.scalar(select(BooksModel).where(
            BooksModel.title == data.title,
            BooksModel.author == data.author,
            BooksModel.publication_year == data.publication_year,
            BooksModel.publisher == data.publisher,
        ).order_by(BooksModel.id).limit(1))

    async def create_book(self, data, session):
        book = BooksModel(**data.model_dump(exclude={"quantity"}))
        session.add(book)
        await session.flush()
        return book

    async def add_copies(self, book_id, quantity, session):
        for _ in range(quantity):
            session.add(BookCopiesModel(book_id=book_id))
        await session.flush()

    async def save_document(self, document_id, payload_hash, result, session):
        session.add(PurchaseImportModel(document_id=document_id, payload_hash=payload_hash, result=result))
        await session.flush()
