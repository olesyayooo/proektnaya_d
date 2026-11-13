import unittest
from unittest.mock import patch
from sqlalchemy import select, func
from fastapi.testclient import TestClient
import test_library
from main import app
from src.database import get_db
from src.configs import settings
from pydantic import SecretStr
from src.books.models import BooksModel, BookCopiesModel
from src.integration.models import PurchaseImportModel
from src.integration.repository import IntegrationRepository


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    tearDown = test_library.LibraryTests.tearDown

    def setUp(self):
        test_library.LibraryTests.setUp(self)
        async def session_override():
            yield self.session
        app.dependency_overrides[get_db] = session_override
        self.key_patch = patch.object(settings, "INTEGRATION_API_KEY", SecretStr("integration-test-key"))
        self.key_patch.start()
        self.addCleanup(self.key_patch.stop)
        self.client = TestClient(app)
        self.item = {'title': self.book.title, 'author': self.book.author,
                     'publication_year': self.book.publication_year, 'publisher': self.book.publisher, 'quantity': 2}
        self.body = {'document_id': '1c-document-001', 'books': [self.item, {**self.item, 'publication_year': 2025, 'quantity': 3}]}

    def count(self, model):
        return self.db.scalar(select(func.count()).select_from(model))

    def login(self):
        self.client.headers["X-Integration-Key"] = "integration-test-key"

    def test_import_retry_and_conflict(self):
        self.login()
        response = self.client.post('/integration/purchases', json=self.body)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()['data']
        self.assertEqual(result['created_books'], 1)
        self.assertEqual(result['created_copies'], 5)
        self.assertFalse(result['already_imported'])
        self.assertEqual(self.count(BooksModel), 2)
        self.assertEqual(self.count(BookCopiesModel), 6)
        self.assertEqual(self.count(PurchaseImportModel), 1)
        retry = self.client.post('/integration/purchases', json={**self.body, 'books': self.body['books'][::-1]})
        self.assertTrue(retry.json()['data']['already_imported'])
        self.assertEqual(self.count(BookCopiesModel), 6)
        conflict = self.client.post('/integration/purchases', json={**self.body, 'books': [self.item]})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()['detail']['error'], 'PURCHASE_DOCUMENT_CONFLICT')
        another = self.client.post('/integration/purchases', json={**self.body, 'document_id': '002'})
        self.assertEqual(another.status_code, 200, another.text)
        self.assertEqual(another.json()['data']['created_books'], 0)
        self.assertEqual(self.count(BookCopiesModel), 11)

    def test_auth_and_validation(self):
        self.assertEqual(self.client.post('/integration/purchases', json=self.body).status_code, 401)
        self.client.headers["X-Integration-Key"] = "incorrect"
        self.assertEqual(self.client.post('/integration/purchases', json=self.body).status_code, 401)
        with patch.object(settings, "INTEGRATION_API_KEY", None):
            self.assertEqual(self.client.post('/integration/purchases', json=self.body).status_code, 503)
        self.login()
        for body in [
            {**self.body, 'books': []}, {**self.body, 'document_id': ' '},
            {**self.body, 'books': [{**self.item, 'quantity': 0}]},
            {**self.body, 'books': [{**self.item, 'quantity': 1.5}]},
            {**self.body, 'books': [{**self.item, 'title': ' '}]},
            {**self.body, 'books': [{**self.item, 'publication_year': -1}]},
            {**self.body, 'books': [{**self.item, 'quantity': 1000}] * 6},
        ]:
            response = self.client.post('/integration/purchases', json=body)
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.count(PurchaseImportModel), 0)

    def test_rollback_and_duplicate_positions(self):
        self.login()
        with patch.object(IntegrationRepository, 'save_document', side_effect=RuntimeError('simulated failure')):
            with self.assertRaises(RuntimeError):
                self.client.post('/integration/purchases', json=self.body)
        self.assertEqual(self.count(BooksModel), 1)
        self.assertEqual(self.count(BookCopiesModel), 1)
        self.assertEqual(self.count(PurchaseImportModel), 0)
        response = self.client.post('/integration/purchases', json={**self.body, 'books': [self.item, self.item]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['data']['created_copies'], 4)
        self.assertEqual(len(response.json()['data']['books']), 1)
        retry = self.client.post('/integration/purchases', json={**self.body, 'books': [{**self.item, 'quantity': 4}]})
        self.assertTrue(retry.json()['data']['already_imported'])
