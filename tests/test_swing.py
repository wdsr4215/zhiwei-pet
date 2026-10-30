import unittest
from zhiwei.swing import swing_projection
class SwingTests(unittest.TestCase):
 def test_front_back_projection(self):
  front,rise_front=swing_projection(5.25)
  back,rise_back=swing_projection(7.35)
  self.assertGreater(front,1);self.assertLess(back,1)
  self.assertAlmostEqual(rise_front,rise_back)
  self.assertEqual(swing_projection(0),(1,0))
 def test_bounds_for_full_cycle(self):
  for i in range(1000):
   scale,rise=swing_projection(i*.02)
   self.assertTrue(.9<scale<1.1);self.assertTrue(0<=rise<9)
if __name__=='__main__':unittest.main()
