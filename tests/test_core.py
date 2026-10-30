import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
import requests
from zhiwei.storage import Store
from zhiwei import ai


class LocalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'test.db'
        self.store = Store(self.path)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def test_notes_persist_and_search(self):
        self.store.add_note('鲸鱼的灵感')
        self.store.db.close()
        self.store = Store(self.path)
        self.assertEqual(self.store.notes('灵感')[0]['body'], '鲸鱼的灵感')
        self.assertEqual(len(self.store.notes('不存在')), 0)

    def test_overdue_restart_ack_and_snooze(self):
        now = datetime(2026, 10, 30, 12)
        self.store.add_reminder('休息', now - timedelta(hours=2))
        ident = self.store.due_reminders(now)[0]['id']
        self.store.db.close()
        self.store = Store(self.path)
        self.assertEqual(len(self.store.due_reminders(now)), 1)
        self.store.finish_reminder(ident, snooze=True, now=now)
        self.assertEqual(len(self.store.due_reminders(now)), 0)
        self.assertEqual(len(self.store.due_reminders(now + timedelta(minutes=5))), 1)
        self.store.finish_reminder(ident, now=now)
        self.assertEqual(len(self.store.due_reminders(now + timedelta(days=2))), 0)

    def test_recurring_skips_missed_days(self):
        now = datetime(2026, 10, 30, 12)
        self.store.add_reminder('每天', now - timedelta(days=3), 'daily')
        ident = self.store.due_reminders(now)[0]['id']
        self.store.finish_reminder(ident, now=now)
        self.assertEqual(self.store.reminders()[0]['due'], '2026-10-31T12:00:00')

    def test_usage_separated_by_provider(self):
        self.store.record_usage('DeepSeek', 'a', {'prompt_tokens': 12, 'completion_tokens': 3}, 'test')
        self.store.record_usage('OpenAI', 'b', {'prompt_tokens': 2}, 'test2')
        self.assertEqual(len(self.store.usage_summary()), 2)


class APITests(unittest.TestCase):
    config = {'provider': 'DeepSeek', 'url': 'https://api.deepseek.com', 'model': 'deepseek-flash'}

    def test_reject_unsafe_remote_url(self):
        for url in ['http://example.org', 'https://key@example.org', 'https://example.org?key=x']:
            with self.assertRaises(ai.AIError):
                ai.validate_url(url)
        self.assertEqual(ai.validate_url('http://localhost:1234/v1/'), 'http://localhost:1234/v1')

    @patch('zhiwei.ai.requests.request')
    def test_chat_contract(self, request):
        request.return_value = Mock(status_code=200)
        request.return_value.json.return_value = {'choices': [{'message': {'content': '你好'}}], 'usage': {'prompt_tokens': 3}}
        result = ai.chat(self.config, [{'role': 'user', 'content': '你好'}], 'test-key')
        self.assertEqual(result['text'], '你好')
        self.assertEqual(result['usage']['prompt_tokens'], 3)
        self.assertFalse(request.call_args.kwargs['allow_redirects'])
        self.assertEqual(request.call_args.args[1], 'https://api.deepseek.com/chat/completions')

    @patch('zhiwei.ai.requests.request')
    def test_errors_dont_leak_credentials(self, request):
        request.side_effect = requests.ConnectionError('secret-token-in-request')
        with self.assertRaises(ai.AIError) as caught:
            ai.chat(self.config, [], 'secret-token')
        self.assertNotIn('secret', str(caught.exception))
        request.side_effect = None
        request.return_value = Mock(status_code=401)
        with self.assertRaisesRegex(ai.AIError, '密钥无效'):
            ai.chat(self.config, [], 'test')

    @patch('zhiwei.ai.requests.request')
    def test_balance_contract_and_no_guess(self, request):
        request.return_value = Mock(status_code=200)
        request.return_value.json.return_value = {'is_available': True, 'balance_infos': [{'currency': 'CNY', 'total_balance': '1.2', 'granted_balance': '0', 'topped_up_balance': '1.2'}]}
        self.assertEqual(ai.balance(self.config, 'test')['balance_infos'][0]['total_balance'], '1.2')
        with self.assertRaises(ai.AIError):
            ai.balance({'provider': 'OpenAI', 'url': 'https://api.openai.com/v1'}, 'test')


if __name__ == '__main__':
    unittest.main()
