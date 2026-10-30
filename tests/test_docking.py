import tempfile,unittest,time
from pathlib import Path
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect
from zhiwei.storage import Store
from zhiwei.pet import Pet
from zhiwei.docking import nearby_edge,snap_position

class DockTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_edges_with_negative_monitor(self):
  area=QRect(-1920,0,1920,1040)
  self.assertEqual(nearby_edge(QRect(-1910,400,300,400),area),'left')
  self.assertIsNone(nearby_edge(QRect(-1000,300,300,400),area))
  self.assertEqual(snap_position(QRect(-400,400,300,400),area,'right'),(-300,400))
 def test_dock_stays_silent_persistent_and_releases(self):
  with tempfile.TemporaryDirectory() as d:
   store=Store(Path(d)/'db'); pet=Pet(Path('assets/character.png').resolve(),store)
   pet.voice.play=Mock();pet.dock('right');pos=pet.pos()
   pet.next_idle=0;pet.until=0
   pet.tick();pet.react('happy','不该说话');pet.notify('water','喝水');pet.tick()
   self.assertEqual(pet.pos(),pos);self.assertEqual(pet.state,'docked');pet.voice.play.assert_not_called()
   self.assertEqual(store.get('dock_side'),'right')
   pet.undock();self.assertEqual(pet.state,'idle');self.assertIsNone(store.get('dock_side'))
   pet.dock('left');restored=Pet(Path('assets/character.png').resolve(),store)
   self.assertEqual(restored.state,'docked');restored.timer.stop();restored.fan.clock.stop();restored.close()
   pet.walk();self.assertIsNone(pet.dock_side);self.assertEqual(pet.state,'walk')
   pet.timer.stop();pet.fan.clock.stop();pet.close();store.db.close()
if __name__=='__main__':unittest.main()
