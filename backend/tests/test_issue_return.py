import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4
from unittest.mock import AsyncMock
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from fastapi.testclient import TestClient
import test_library
from main import app
from src.database import get_db
from src.auth.dependencies import get_current_user
from src.loans.service import LoansService
from src.loans.schemas import LoanCreate


class IssueReturnTests(unittest.IsolatedAsyncioTestCase):
    tearDown = test_library.LibraryTests.tearDown

    def setUp(self):
        test_library.LibraryTests.setUp(self)
        self.reader.reader_card = 1234567890
        self.db.commit()
        self.book_id = self.book.id
        self.loan_id = self.loan.id
        self.today = datetime.now(ZoneInfo('Europe/Moscow')).date()
        async def session_override():
            yield self.session
        app.dependency_overrides[get_db] = session_override
        self.client = TestClient(app)
        self.body = {'book_id': str(self.book_id), 'reader_card': 1234567890, 'due_date': self.today.isoformat()}

    def login(self, user):
        app.dependency_overrides[get_current_user] = lambda: user

    def test_return_issue_and_availability(self):
        self.login(self.librarian)
        blocked = self.client.post('/loans', json=self.body)
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertEqual(blocked.json()['detail']['error'], 'NO_AVAILABLE_COPIES')
        returned = self.client.post(f'/loans/{self.loan_id}/return')
        self.assertEqual(returned.status_code, 200, returned.text)
        timestamp = returned.json()['data']['returned_at']
        self.assertIsNotNone(timestamp)
        self.assertTrue(self.client.get(f'/books/{self.book_id}').json()['data']['available'])
        repeated = self.client.post(f'/loans/{self.loan_id}/return')
        self.assertEqual(repeated.status_code, 409)
        self.assertEqual(repeated.json()['detail']['error'], 'LOAN_ALREADY_RETURNED')
        issued = self.client.post('/loans', json=self.body)
        self.assertEqual(issued.status_code, 201, issued.text)
        data = issued.json()['data']
        self.assertEqual(data['reader_id'], str(self.reader.id))
        self.assertEqual(data['librarian_id'], str(self.librarian.id))
        self.assertEqual(data['copy_id'], str(self.copy.id))
        self.assertIsNone(data['returned_at'])
        self.assertFalse(self.client.get(f'/books/{self.book_id}').json()['data']['available'])
        self.login(self.reader)
        active = self.client.get('/loans/me?status=active').json()
        self.assertEqual(active['total'], 1)
        self.assertEqual(active['data'][0]['id'], data['id'])
        self.assertEqual(self.client.get('/loans/me?status=returned').json()['total'], 1)

    def test_errors_and_authorization(self):
        for path, body in [('/loans', self.body), (f'/loans/{self.loan_id}/return', None)]:
            self.assertEqual(self.client.post(path, json=body).status_code, 401)
            self.login(self.reader)
            self.assertEqual(self.client.post(path, json=body).status_code, 403)
            app.dependency_overrides.pop(get_current_user)
        self.login(self.librarian)
        cases = [
            ({**self.body, 'book_id': str(uuid4())}, 404, 'BOOK_NOT_FOUND'),
            ({**self.body, 'reader_card': 999999}, 404, 'READER_NOT_FOUND'),
            ({**self.body, 'due_date': (self.today - timedelta(days=1)).isoformat()}, 400, 'INVALID_DUE_DATE'),
        ]
        for body, code, error in cases:
            response = self.client.post('/loans', json=body)
            self.assertEqual(response.status_code, code, response.text)
            self.assertEqual(response.json()['detail']['error'], error)
        self.assertEqual(self.client.post('/loans', json={**self.body, 'reader_card': -1}).status_code, 422)
        missing = self.client.post(f'/loans/{uuid4()}/return')
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()['detail']['error'], 'LOAN_NOT_FOUND')

    async def test_unique_constraint_conflict_handling(self):
        repo = AsyncMock()
        repo.get_reader_by_card.return_value = self.reader
        repo.get_free_copy.return_value = self.copy
        original = Exception('duplicate')
        original.constraint_name = 'uq_loans_active_copy'
        repo.create.side_effect = IntegrityError('insert', {}, original)
        session = AsyncMock()
        service = LoansService(repo)
        with self.assertRaises(HTTPException) as caught:
            await service.issue(LoanCreate(**self.body), self.librarian, session)
        self.assertEqual(caught.exception.status_code, 409)
        session.rollback.assert_awaited_once()
        original.constraint_name = 'some_other_constraint'
        with self.assertRaises(IntegrityError):
            await service.issue(LoanCreate(**self.body), self.librarian, session)
