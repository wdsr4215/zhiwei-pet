"""单一提醒呈现 owner：持久化队列依次展示，不同时叠出多个弹窗。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QSystemTrayIcon


class ReminderPresenter:
    def __init__(self, store, pet, panel, tray, beep, dialog_factory=QMessageBox):
        self.store, self.pet, self.panel, self.tray = store, pet, panel, tray
        self.beep, self.dialog_factory = beep, dialog_factory
        self.active = None
        self.active_id = None

    def tick(self):
        pending_ids = {r['id'] for r in self.store.reminders()}
        if self.active and self.active_id not in pending_ids:
            self.active.blockSignals(True)
            self.active.close()
            self.active.deleteLater()
            self.active, self.active_id = None, None
        if self.store.get('quiet', False):
            if self.active:
                self.active.hide()
            return
        if self.active:
            self.active.show()
            return
        rows = self.store.due_reminders()
        if not rows:
            return
        row = rows[0]
        kind = self.store.reminder_kind(row['id'])
        self.pet.show()
        self.pet.notify(kind, row['title'][:60])
        self.tray.showMessage('知微提醒你', row['title'], QSystemTrayIcon.Information, 10000)
        self.beep()
        box = self.dialog_factory(QMessageBox.Information, '知微 · 到时间了', row['title'], parent=None)
        box.setWindowFlag(Qt.WindowStaysOnTopHint)
        done = box.addButton('知道了', QMessageBox.AcceptRole)
        snooze = box.addButton('5 分钟后再提醒', QMessageBox.ActionRole)
        box.setDefaultButton(done)
        self.active, self.active_id = box, row['id']

        def acknowledged(result):
            self.store.finish_reminder(row['id'], snooze=box.clickedButton() == snooze)
            self.active, self.active_id = None, None
            self.panel.refresh_reminders()
            box.deleteLater()
        box.finished.connect(acknowledged)
        box.show()
