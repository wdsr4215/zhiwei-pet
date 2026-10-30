import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock
from zhiwei.storage import Store
from zhiwei.notifications import ReminderPresenter


class FakeDialog:
    def __init__(self, *args, **kwargs):
        self.finished = Mock()
        self.finished.connect.side_effect = lambda callback: setattr(self, 'callback', callback)
        self.visible = False
        self.buttons = []
        self.selected = None
        self.blocked = False

    def setWindowFlag(self, flag): pass
    def setDefaultButton(self, button): pass
    def deleteLater(self): pass
    def blockSignals(self, value): self.blocked = value
    def addButton(self, label, role):
        self.buttons.append(label)
        return label
    def clickedButton(self): return self.selected
    def show(self): self.visible = True
    def hide(self): self.visible = False
    def close(self): self.visible = False
    def acknowledge(self):
        self.selected = self.buttons[0]
        self.callback(0)


class ReminderDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / 'test.db')
        self.pet, self.panel, self.tray, self.beep = Mock(), Mock(), Mock(), Mock()
        self.presenter = ReminderPresenter(self.store, self.pet, self.panel, self.tray, self.beep, FakeDialog)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def test_two_overdue_notifications_are_serialized_with_kind(self):
        now = datetime.now() - timedelta(seconds=3)
        self.store.add_reminder('喝水', now, kind='water')
        self.store.add_reminder('专注完成', now + timedelta(seconds=1), kind='focus')
        self.presenter.tick()
        first = self.presenter.active
        self.pet.notify.assert_called_once_with('water', '喝水')
        self.presenter.tick()
        self.assertIs(first, self.presenter.active)
        self.assertEqual(self.beep.call_count, 1)
        first.acknowledge()
        self.presenter.tick()
        self.pet.notify.assert_called_with('focus', '专注完成')
        self.assertEqual(self.beep.call_count, 2)

    def test_quiet_hides_without_acknowledging_then_resumes(self):
        self.store.add_reminder('休息', datetime.now() - timedelta(seconds=1))
        self.presenter.tick()
        dialog = self.presenter.active
        self.store.set('quiet', True)
        self.presenter.tick()
        self.assertFalse(dialog.visible)
        self.assertEqual(len(self.store.reminders()), 1)
        self.store.set('quiet', False)
        self.presenter.tick()
        self.assertTrue(dialog.visible)
        self.assertEqual(self.beep.call_count, 1)

    def test_cancelled_active_recurring_reminder_is_not_recreated(self):
        self.store.add_reminder('每天', datetime.now() - timedelta(seconds=1), 'daily')
        self.presenter.tick()
        ident = self.presenter.active_id
        dialog = self.presenter.active
        self.store.cancel_reminder(ident)
        self.presenter.tick()
        self.assertTrue(dialog.blocked)
        self.assertIsNone(self.presenter.active)
        self.store.finish_reminder(ident)
        self.assertEqual(len(self.store.reminders()), 0)

    def test_snooze_does_not_move_daily_schedule(self):
        now = datetime(2026, 10, 30, 12)
        self.store.add_reminder('午间休息', now, 'daily')
        ident = self.store.due_reminders(now)[0]['id']
        self.store.finish_reminder(ident, snooze=True, now=now)
        self.store.finish_reminder(ident, now=now + timedelta(minutes=5))
        self.assertEqual(self.store.reminders()[0]['due'], '2026-10-31T12:00:00')

    def test_legacy_reminder_snooze_keeps_original_schedule(self):
        now = datetime(2026, 10, 30, 12)
        with self.store.db:
            self.store.db.execute('INSERT INTO reminders(title,due,repeat) VALUES (?,?,?)', ('旧提醒', now.isoformat(), 'weekly'))
        ident = self.store.due_reminders(now)[0]['id']
        self.store.finish_reminder(ident, snooze=True, now=now)
        self.store.finish_reminder(ident, now=now + timedelta(minutes=5))
        self.assertEqual(self.store.reminders()[0]['due'], '2026-11-06T12:00:00')
