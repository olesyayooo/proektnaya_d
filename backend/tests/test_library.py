import unittest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
from main import app
from src.database import Base, get_db
from src.auth.dependencies import get_current_user
from src.auth.models import UsersModel
from src.auth.repository import AuthRepository
from src.auth.schemas import UserOutMe, UserRole
from src.books.models import BooksModel, BookCopiesModel
from src.books.repository import BooksRepository
from src.books.dependencies import get_books_service
from src.books.service import BooksService
from src.loans.models import LoansModel
from src.loans.repository import LoansRepository


class AsyncSessionAdapter:
    def __init__(self, session):
        self.session = session

    async def execute(self, query):
        return self.session.execute(query)

    async def scalar(self, query):
        return self.session.scalar(query)

    async def scalars(self, query):
        return self.session.scalars(query)


class LibraryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.session = AsyncSessionAdapter(self.db)
        self.reader = UsersModel(name='Reader', email='reader@example.com', hashed_password='hash', role=UserRole.reader)
        self.librarian = UsersModel(name='Librarian', email='staff@example.com', hashed_password='hash', role=UserRole.librarian)
        self.book = BooksModel(title='War and Peace', author='Leo Tolstoy', publication_year=1869, publisher='Publisher')
        self.db.add_all([self.reader, self.librarian, self.book])
        self.db.flush()
        self.copy = BookCopiesModel(book_id=self.book.id)
        self.db.add(self.copy)
        self.db.flush()
        self.loan = LoansModel(copy_id=self.copy.id, reader_id=self.reader.id, librarian_id=self.librarian.id,
                               issued_at=datetime(2026, 1, 1, tzinfo=timezone.utc), due_date=date(2026, 1, 15))
        self.db.add(self.loan)
        self.db.commit()
        self.service = BooksService(BooksRepository(), LoansRepository())

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    async def test_availability_search_and_pagination(self):
        result = await self.service.catalog(self.session, 'Tolstoy war', False, 0, 20)
        self.assertEqual(result['total'], 1)
        self.assertFalse(result['data'][0].available)
        self.assertEqual((await self.service.catalog(self.session, 'war', True, 0, 20))['total'], 0)
        self.db.add(BookCopiesModel(book_id=self.book.id))
        self.db.commit()
        self.assertEqual((await self.service.catalog(self.session, 'WAR tolstoy', True, 0, 20))['total'], 1)
        self.assertEqual((await self.service.catalog(self.session, '%', None, 1, 20))['data'], [])
        self.assertEqual((await self.service.catalog(self.session, 'unknown', None, 0, 20))['total'], 0)

    async def test_returned_and_no_copies(self):
        self.loan.returned_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.db.commit()
        result = await self.service.get_book(self.book.id, self.librarian, self.session)
        self.assertTrue(result['data'].available)
        self.assertEqual(result['data'].active_loans, [])
        self.db.add(BooksModel(title='No copies', author='Author', publication_year=2020, publisher='P'))
        self.db.commit()
        self.assertEqual((await self.service.catalog(self.session, 'No copies', False, 0, 20))['total'], 1)

    async def test_unique_active_copy(self):
        self.db.add(LoansModel(copy_id=self.copy.id, reader_id=self.reader.id, librarian_id=self.librarian.id,
                              issued_at=datetime(2026, 1, 2), due_date=date(2026, 1, 15)))
        with self.assertRaises(IntegrityError):
            self.db.flush()
        self.db.rollback()

    def test_reader_card_serialization(self):
        for role in UserRole:
            data = UserOutMe(name='Name', email='user@example.com', role=role, reader_card=123).model_dump()
            self.assertEqual('reader_card' in data, role == UserRole.reader)

    def test_http_role_visibility(self):
        async def session_override():
            yield self.session
        app.dependency_overrides[get_db] = session_override
        app.dependency_overrides[get_books_service] = lambda: self.service
        client = TestClient(app)
        for user in [self.reader, self.librarian]:
            app.dependency_overrides[get_current_user] = lambda: user
            response = client.get(f'/books/{self.book.id}')
            self.assertEqual(response.status_code, 200, response.text)
            data = response.json()['data']
            self.assertEqual('active_loans' in data, user.role == UserRole.librarian)
            if user.role == UserRole.librarian:
                self.assertEqual(data['active_loans'][0]['reader_id'], str(self.reader.id))
            self.assertEqual(client.get(f'/books/{uuid4()}').status_code, 404)
            self.assertEqual(client.get('/books?limit=101').status_code, 422)
            me = client.get('/auth/me').json()['data']
            self.assertEqual('reader_card' in me, user.role == UserRole.reader)
        app.dependency_overrides.pop(get_current_user)
        self.assertEqual(client.get('/books').status_code, 401)

    async def test_card_conflict_retry_and_other_errors(self):
        user = UsersModel(name='New', email='new@example.com', hashed_password='hash')
        original = Exception('duplicate')
        original.constraint_name = 'uq_users_reader_card'
        conflict = IntegrityError('insert', {}, original)
        session = AsyncMock()
        session.add = lambda obj: None
        session.commit.side_effect = [conflict, None]
        with patch('src.auth.repository.randbelow', side_effect=[1, 2]):
            await AuthRepository().register_user(user, session)
        self.assertEqual(user.reader_card, 1_000_000_002)
        session.rollback.assert_awaited_once()
        original.constraint_name = 'users_email_key'
        session.commit.side_effect = conflict
        with self.assertRaises(IntegrityError):
            await AuthRepository().register_user(user, session)
