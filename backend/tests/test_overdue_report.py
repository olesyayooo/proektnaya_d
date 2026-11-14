import unittest
from unittest.mock import patch
from pydantic import SecretStr
import test_reader_loans
import test_library
from src.configs import settings


class OverdueReportTests(unittest.IsolatedAsyncioTestCase):
    tearDown = test_library.LibraryTests.tearDown

    def setUp(self):
        test_reader_loans.ReaderLoansTests.setUp(self)
        key_patch = patch.object(settings, 'INTEGRATION_API_KEY', SecretStr('report-test-key'))
        key_patch.start()
        self.addCleanup(key_patch.stop)

    def test_report_auth_filters_and_details(self):
        path = '/integration/overdue-report'
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get(path, headers={'X-Integration-Key': 'wrong'}).status_code, 401)
        self.client.headers['X-Integration-Key'] = 'report-test-key'
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data['total'], 1)
        item = data['data'][0]
        self.assertEqual(item['status'], 'active')
        self.assertTrue(item['overdue'])
        self.assertEqual(item['overdue_days'], 1)
        self.assertEqual(item['id'], str(self.loan.id))
        self.assertEqual(item['reader']['name'], self.reader.name)
        self.assertEqual(item['reader']['reader_card'], 1234567890)
        self.assertEqual(item['book']['title'], self.book.title)
        self.assertIn('issued_at', item)
        self.assertIn('due_date', item)
        self.assertIsNone(item['returned_at'])
        returned = self.client.get(path + '?status=returned').json()
        self.assertEqual(returned['total'], 1)
        self.assertEqual(returned['data'][0]['status'], 'returned')
        self.assertEqual(returned['data'][0]['overdue_days'], 2)
        all_loans = self.client.get(path + '?status=all').json()
        self.assertEqual(all_loans['total'], 2)
        self.assertTrue(all(item['overdue'] for item in all_loans['data']))
        page = self.client.get(path + '?status=all&limit=1&skip=1').json()
        self.assertEqual(page['total'], 2)
        self.assertEqual(len(page['data']), 1)
        self.assertEqual(self.client.get(path + '?status=all&skip=2').json()['data'], [])

    def test_report_validation_and_empty_result(self):
        self.client.headers['X-Integration-Key'] = 'report-test-key'
        path = '/integration/overdue-report'
        for query in ['status=bad', 'skip=-1', 'limit=0', 'limit=1001']:
            self.assertEqual(self.client.get(path + '?' + query).status_code, 422)
        # Returning on the deadline is not late; no current overdue loans remain.
        self.loan.returned_at = self.loan.issued_at
        self.db.commit()
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total'], 0)
        self.assertEqual(response.json()['data'], [])
        with patch.object(settings, 'INTEGRATION_API_KEY', None):
            self.assertEqual(self.client.get(path).status_code, 503)
