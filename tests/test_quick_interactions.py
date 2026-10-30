import unittest,tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication
from zhiwei.storage import Store
from zhiwei.pet import Pet
from zhiwei.panel import Panel
from zhiwei.activities import ActivityClock
from zhiwei.quick_interactions import QuickInteractions

class QuickTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def test_quick_routes_and_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'test.db')
            pet=Pet(Path('assets/character.png').resolve(),store)
            clock=ActivityClock(store); panel=Panel(store,pet,clock)
            quick=QuickInteractions(pet,panel,clock); pet.quick_action.connect(quick.open)
            for kind in ('note','chat','clock','wallet','play'):
                quick.open(kind)
                self.assertFalse(panel.isVisible())
                self.assertTrue(quick.windows[kind].isVisible())
            note=quick.windows['note']; note.input.setPlainText('便签验证'); note.save_note()
            self.assertEqual(store.notes()[0]['body'],'便签验证')
            reminder=quick.windows['clock']; reminder.input.setText('测试提醒'); reminder.remind()
            self.assertEqual(store.reminders()[0]['title'],'测试提醒')
            quick.open('chat'); chat=quick.windows['chat']; chat.input.setText('测试问答')
            panel.run_job=lambda fn,done,failed: failed('模拟网络不可用')
            chat.chat(); self.assertTrue(chat.send.isEnabled()); self.assertEqual(chat.input.text(),'测试问答')
            self.assertFalse(panel.isVisible())
            for w in quick.windows.values(): w.close()
            clock.timer.stop(); pet.close(); panel.close(); store.db.close()
if __name__=='__main__': unittest.main()
