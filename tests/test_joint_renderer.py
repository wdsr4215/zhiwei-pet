import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import Qt,QRectF
from zhiwei.joint_renderer import JointRenderer
class JointTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_all_parts_and_continuous_frames(self):
  rig=JointRenderer(Path('assets/sprites/joints.png'));self.assertTrue(rig.ready)
  for state in ('walk','idle','eat','play'):
   frames=[]
   for t in (1,1+1/60):
    image=QImage(320,420,QImage.Format_ARGB32);image.fill(Qt.transparent)
    painter=QPainter(image);rig.draw(painter,QRectF(0,0,320,420),state,t);painter.end();frames.append(bytes(image.bits()))
   self.assertNotEqual(frames[0],frames[1],state)
if __name__=='__main__':unittest.main()
