"""Real HTTP + PostgreSQL check. Run from backend, see README.md.

--send creates a persistent demo receipt; without it this is read-only.
Never prints the integration key or database URL.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.configs import settings
from src.books.models import BooksModel, BookCopiesModel
from src.integration.models import PurchaseImportModel


async def inspect_receipt(factory, document_id):
    async with factory() as db:
        receipt = await db.scalar(select(PurchaseImportModel).where(
            PurchaseImportModel.document_id == document_id))
        if receipt is None:
            return None
        result = receipt.result
        books = []
        from uuid import UUID
        for item in result['books']:
            book_id = UUID(item['book_id'])
            book = await db.get(BooksModel, book_id)
            assert book is not None, 'Receipt references a missing book'
            copies = await db.scalar(select(func.count()).select_from(BookCopiesModel).where(
                BookCopiesModel.book_id == book_id))
            assert copies >= item['quantity'], 'Not enough physical copies'
            books.append({'book_id': str(book_id), 'title': book.title,
                          'receipt_quantity': item['quantity'], 'total_copies': copies})
        return {'document_id': receipt.document_id, 'result': result, 'books': books}


async def main(args):
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    if engine.dialect.name != 'postgresql':
        raise RuntimeError('This check requires PostgreSQL')
    factory = async_sessionmaker(engine)
    try:
        if args.send:
            if not settings.INTEGRATION_API_KEY:
                raise RuntimeError('INTEGRATION_API_KEY is not configured')
            payload = {
                'document_id': args.document_id,
                'books': [{'title': 'Мастер и Маргарита', 'author': 'Михаил Булгаков',
                           'publication_year': 1967, 'publisher': 'Тест интеграции 1С MVP',
                           'quantity': 5}],
            }
            async with httpx.AsyncClient(base_url=args.url, timeout=30) as client:
                headers = {'X-Integration-Key': settings.INTEGRATION_API_KEY.get_secret_value()}
                first = await client.post('/integration/purchases', json=payload, headers=headers)
                assert first.status_code == 200, f'Import HTTP {first.status_code}'
                result = first.json()['data']
                assert result['created_copies'] == 5
                before_retry = await inspect_receipt(factory, args.document_id)
                assert before_retry is not None
                retry = await client.post('/integration/purchases', json=payload, headers=headers)
                assert retry.status_code == 200
                assert retry.json()['data']['already_imported'] is True
                conflict = await client.post('/integration/purchases', headers=headers,
                    json={**payload, 'books': [{**payload['books'][0], 'quantity': 6}]})
                assert conflict.status_code == 409
                unauthorized = await client.post('/integration/purchases', json=payload)
                assert unauthorized.status_code == 401
                invalid = await client.post('/integration/purchases', headers=headers,
                    json={**payload, 'books': [{**payload['books'][0], 'quantity': 0}]})
                assert invalid.status_code == 422
                after_retry = await inspect_receipt(factory, args.document_id)
                assert before_retry == after_retry, 'Retry or rejected request changed PostgreSQL data'
                print('HTTP: import=200, retry=200 (already_imported), conflict=409, no key=401, invalid=422')
                print('PostgreSQL: copy counts unchanged after retry and rejected requests')
        receipt = await inspect_receipt(factory, args.document_id)
        if receipt is None:
            raise RuntimeError('Document not found in PostgreSQL: ' + args.document_id)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    finally:
        await engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document-id', required=True, help='Exact ID from 1C JSON, including 1c: prefix')
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--send', action='store_true', help='Create/retry a persistent HTTP demo receipt')
    asyncio.run(main(parser.parse_args()))
