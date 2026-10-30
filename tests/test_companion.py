import unittest,time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from zhiwei.pet import Pet
from zhiwei.storage import Store
from zhiwei.panel import Panel
from zhiwei.activities import ActivityClock
from zhiwei.quick_interactions import QuickInteractions
from zhiwei.pet_theme import PlayTile
class CompanionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.store=Store(':memory:');self.pet=Pet(Path('assets/character.png').resolve(),self.store)
 def tearDown(self):self.pet.timer.stop();self.pet.fan.clock.stop();self.pet.close();self.store.db.close()
 def test_polished_tile_keeps_text_area(self):
  clock=ActivityClock(self.store);panel=Panel(self.store,self.pet,clock);quick=QuickInteractions(self.pet,panel,clock);quick.open('play');self.app.processEvents()
  tiles=quick.windows['play'].findChildren(PlayTile)
  self.assertEqual(len(tiles),8)
  for tile in tiles:self.assertGreaterEqual(tile.height(),96);self.assertTrue(tile.title);self.assertTrue(tile.subtitle)
  quick.windows['play'].close();panel.close();clock.timer.stop()
 def test_walk_does_not_reset_schedule_and_rest_follows(self):
  routine=self.pet.routine;routine.bag=['walk','swing','play','tired','drink','daydream'];routine.due=0
  self.pet.can_peek_nearby=lambda:False
  now=time.monotonic();routine.tick(now)
  self.assertEqual(self.pet.state,'walk');self.assertTrue(routine.active)
  self.assertEqual(routine.bag[0],'swing')
  self.pet.state='idle';self.pet.target_x=None;routine.tick(now+5)
  self.assertFalse(routine.active);self.assertGreaterEqual(routine.due,now+40)
  routine.tick(routine.due+.1)
  self.assertEqual(self.pet.state,'swing');self.assertGreaterEqual(self.pet.until-time.monotonic(),59)
  self.assertEqual(routine.bag[0],'play')
 def test_all_nonmoving_actions_get_turns(self):
  r=self.pet.routine;r.bag=['swing','play','tired','drink','daydream'];r.due=0
  seen=[];now=time.monotonic()
  for i in range(5):
   r.tick(max(now,r.due)+.1);seen.append(self.pet.state)
   self.pet.state='idle';r.tick(max(now,r.due)+1);now=r.due
  self.assertEqual(seen,['swing','play','tired','drink','daydream'])
 def test_roam_off_does_not_starve_other_actions(self):
  self.store.set('roam',False);r=self.pet.routine;r.bag=['walk']
  selected=[r.choose(time.monotonic()+i*200) for i in range(5)]
  self.assertEqual(set(selected),{'daydream','swing','play','tired','drink'})
 def test_peek_never_changes_position_or_triggers_fall(self):
  self.pet.nearby_window_side=lambda:'left';pos=self.pet.pos();self.pet.peek(automatic=True)
  self.assertEqual(self.pet.pos(),pos);self.assertEqual(self.pet.state,'peek')
  self.pet.until=0;self.pet.routine.due=time.monotonic()+999;self.pet.tick()
  self.assertEqual(self.pet.state,'idle');self.assertEqual(self.pet.pos(),pos)
  self.pet.nearby_window_side=lambda:None;self.pet.peek(automatic=True)
  self.assertEqual(self.pet.state,'daydream');self.assertEqual(self.pet.pos(),pos)
if __name__=='__main__':unittest.main()
