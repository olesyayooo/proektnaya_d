from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4
from fastapi.testclient import TestClient
from main import app
import unittest
import test_library
from src.database import get_db
from src.auth.dependencies import get_current_user
from src.auth.models import UsersModel
from src.auth.schemas import UserRole
from src.books.models import BookCopiesModel
from src.loans.models import LoansModel


class ReaderLoansTests(unittest.IsolatedAsyncioTestCase):
    tearDown = test_library.LibraryTests.tearDown
    def setUp(self):
        test_library.LibraryTests.setUp(self)
        self.today = datetime.now(ZoneInfo('Europe/Moscow')).date()
        self.reader.reader_card = 1234567890
        other = UsersModel(name='Other', email='other@example.com', hashed_password='hash', role=UserRole.reader, reader_card=1234567891)
        self.db.add(other)
        self.db.flush()
        self.other_id = other.id
        self.loan.issued_at = datetime.combine(self.today - timedelta(days=10), datetime.min.time())
        self.loan.due_date = self.today - timedelta(days=1)
        for owner, due, returned in [
            (self.reader.id, self.today, None),
            (self.reader.id, self.today - timedelta(days=2), datetime.combine(self.today, datetime.min.time())),
            (other.id, self.today, None),
        ]:
            copy = BookCopiesModel(book_id=self.book.id)
            self.db.add(copy)
            self.db.flush()
            self.db.add(LoansModel(copy_id=copy.id, reader_id=owner, librarian_id=self.librarian.id,
                                   issued_at=datetime.combine(self.today - timedelta(days=10), datetime.min.time()),
                                   due_date=due, returned_at=returned))
        self.db.commit()
        async def session_override():
            yield self.session
        app.dependency_overrides[get_db] = session_override
        self.client = TestClient(app)

    def login(self, user):
        app.dependency_overrides[get_current_user] = lambda: user

    def test_reader_own_history_and_statuses(self):
        self.login(self.reader)
        result = self.client.get('/loans/me').json()
        self.assertEqual(result['total'], 3)
        self.assertEqual({x['status'] for x in result['data']}, {'active', 'returned'})
        for state in ['active', 'returned']:
            response = self.client.get(f'/loans/me?status={state}')
            self.assertEqual(response.status_code, 200, response.text)
            data = response.json()
            self.assertEqual(data['total'], 2 if state == 'active' else 1)
            self.assertEqual(data['data'][0]['status'], state)
            self.assertEqual(data['data'][0]['book']['title'], self.book.title)
            self.assertEqual(data['data'][0]['reader_id'], str(self.reader.id))
        self.assertEqual(self.client.get('/loans/me?status=bad').status_code, 422)
        page = self.client.get('/loans/me?skip=3&limit=1').json()
        self.assertEqual(page['total'], 3)
        self.assertEqual(page['data'], [])
        self.assertEqual(self.client.get('/loans/me?limit=101').status_code, 422)

    def test_librarian_search_and_reader_history(self):
        self.login(self.librarian)
        response = self.client.get('/readers?reader_card=1234567890')
        self.assertEqual(response.status_code, 200, response.text)
        reader = response.json()['data']
        self.assertEqual(reader['id'], str(self.reader.id))
        self.assertNotIn('hashed_password', reader)
        result = self.client.get(f'/readers/{reader["id"]}/loans?status=active&overdue=true')
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['total'], 1)
        self.assertEqual(result.json()['data'][0]['status'], 'active')
        self.assertTrue(result.json()['data'][0]['overdue'])
        missing = self.client.get('/readers?reader_card=999999')
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()['detail']['error'], 'READER_NOT_FOUND')
        self.assertEqual(self.client.get(f'/readers/{uuid4()}/loans').status_code, 404)
        self.assertEqual(self.client.get(f'/readers/{self.librarian.id}/loans').status_code, 404)
        self.assertEqual(self.client.get('/readers?reader_card=0').status_code, 422)

    def test_access_control(self):
        for path in ['/loans/me', '/readers?reader_card=1234567890', f'/readers/{self.reader.id}/loans']:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.login(self.reader)
        for path in ['/readers?reader_card=1234567890', f'/readers/{self.other_id}/loans', f'/readers/{self.reader.id}/loans']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()['detail']['error'], 'LIBRARIAN_REQUIRED')
        self.login(self.librarian)
        self.assertEqual(self.client.get('/loans/me').json()['total'], 0)


    def test_all_loans_filters_and_details(self):
        self.assertEqual(self.client.get('/loans').status_code, 401)
        self.login(self.reader)
        self.assertEqual(self.client.get('/loans').status_code, 403)
        self.login(self.librarian)
        response = self.client.get('/loans')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['total'], 4)
        for item in response.json()['data']:
            self.assertEqual(item['book']['id'], str(self.book.id))
            self.assertIn('name', item['reader'])
            self.assertIn('reader_card', item['reader'])
            self.assertNotIn('hashed_password', item['reader'])
        expected = [
            ('status=active', 3), ('status=returned', 1),
            ('overdue=true', 2), ('overdue=false', 2),
            ('status=active&overdue=true', 1), ('status=active&overdue=false', 2),
            ('status=returned&overdue=true', 1), ('status=returned&overdue=false', 0),
        ]
        for query, total in expected:
            result = self.client.get(f'/loans?{query}').json()
            self.assertEqual(result['total'], total, query)
            self.assertEqual(len(result['data']), total, query)
            for item in result['data']:
                self.assertEqual(item['overdue'], item['overdue_days'] > 0)
                if item['overdue']:
                    self.assertEqual(item['overdue_days'], 2 if item['status'] == 'returned' else 1)
                else:
                    self.assertEqual(item['overdue_days'], 0)
        page = self.client.get('/loans?overdue=true&skip=1&limit=1').json()
        self.assertEqual(page['total'], 2)
        self.assertEqual(len(page['data']), 1)
        self.assertEqual(self.client.get('/loans?status=overdue').status_code, 422)
        self.login(self.reader)
        self.assertEqual(self.client.get('/loans/me?overdue=true').json()['total'], 2)
        self.assertEqual(self.client.get('/loans/me?status=active&overdue=true').json()['total'], 1)

    def test_returned_overdue_uses_moscow_date(self):
        # 21:30 UTC is already the next calendar day in Moscow.
        from datetime import timezone
        self.loan.due_date = self.today - timedelta(days=2)
        self.loan.returned_at = datetime.combine(
            self.today - timedelta(days=2), datetime.min.time(), tzinfo=timezone.utc
        ).replace(hour=21, minute=30)
        self.db.commit()
        self.login(self.reader)
        result = self.client.get('/loans/me?status=returned&overdue=true').json()
        item = next(x for x in result['data'] if x['id'] == str(self.loan.id))
        self.assertEqual(item['overdue_days'], 1)
        self.loan.returned_at = self.loan.returned_at.replace(hour=20)
        self.db.commit()
        result = self.client.get('/loans/me?status=returned&overdue=false').json()
        item = next(x for x in result['data'] if x['id'] == str(self.loan.id))
        self.assertEqual(item['overdue_days'], 0)
