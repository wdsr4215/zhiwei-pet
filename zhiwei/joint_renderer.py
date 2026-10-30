"""部件关节连续绘制；不以整帧跳切模拟肢体运动。"""
import math
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPixmap,QImage,QPainter,QColor,QPen

class JointRenderer:
    STATES={'idle','happy','thinking','remind','walk','drag','fall','eat','drink','play','sleep','tired'}
    def __init__(self,path):
        self.parts=[]
        sheet=QImage(str(path))
        if sheet.isNull():return
        rectangles=[(0,0,421,440),(421,0,421,442),(842,0,421,446),
                    (0,450,421,340),(421,450,421,340),(842,450,421,340),
                    (0,790,421,456),(421,790,400,456),(821,790,442,456)]
        for rect in rectangles:
            part=sheet.copy(*rect)
            cw,ch=part.width(),part.height()
            # 运行时确定部件有效边界；不修改原始图集。
            left,top,right,bottom=cw,ch,-1,-1
            for y in range(ch):
                for x in range(cw):
                    if part.pixelColor(x,y).alpha()>40:
                        left=min(left,x);right=max(right,x);top=min(top,y);bottom=max(bottom,y)
            if right<left:return
            self.parts.append(QPixmap.fromImage(part.copy(left,top,right-left+1,bottom-top+1)))
    @property
    def ready(self):return len(self.parts)==9
    def draw(self,p,rect,state,t,facing=1):
        if not self.ready:return
        p.save();p.translate(rect.center().x(),rect.bottom());p.scale(rect.height()/420,rect.height()/420)
        if facing<0:p.scale(-1,1)
        p.translate(-180,-420)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        walk=state=='walk'; phase=t*7
        bounce=abs(math.sin(phase))*3 if walk else math.sin(t*1.8)*1.3
        p.translate(0,-bounce)
        def part(i,x,y,w,h,angle=0,anchor=(.5,0)):
            p.save();p.translate(x,y);p.rotate(angle);p.drawPixmap(QRectF(-w*anchor[0],-h*anchor[1],w,h),self.parts[i],QRectF(self.parts[i].rect()));p.restore()
        hair_angle=math.sin(t*1.6-.5)*1.7
        part(2,180,74,236,307,hair_angle)
        stride=math.sin(phase)*14 if walk else math.sin(t*.8)*.7
        part(6,159,290,49,122,stride)
        part(7,200,290,49,122,-stride)
        left=math.sin(phase+math.pi)*12 if walk else math.sin(t*1.5)*2
        right=-left
        if state in ('eat','drink'):left=-28+math.sin(t*2)*4;right=28-math.sin(t*2)*4
        elif state=='play':right=-42+math.sin(t*2)*8
        elif state=='happy':left=24+math.sin(t*4)*8;right=-left
        elif state in ('drag','fall'):left=20;right=-20
        part(3,127,181,70,137,left,(.5,.08))
        part(4,233,181,70,137,right,(.5,.08))
        part(1,180,170,161,156)
        blink=t%5.3>5.13 or state in ('sleep','tired')
        nod=math.sin(t*1.4)*2
        if state in ('sleep','tired'):nod=7+math.sin(t*.8)*2
        part(8 if blink else 0,180,185,147,151,nod,(.5,1))
        wx=284+math.sin(t*1.2)*7;wy=127+math.sin(t*1.8)*9
        if state=='play':wx=259+math.sin(t*1.5)*18;wy=194+math.sin(t*1.5)*12
        part(5,wx,wy,76,55,math.sin(t)*7,(.5,.5))
        if state in ('eat','drink'):
            p.setPen(QPen(QColor('#536fae'),1.5));p.setBrush(QColor('#f1f6ff'))
            if state=='eat':
                p.drawChord(QRectF(154,233,52,38),180*16,180*16);p.setBrush(QColor('#fffdf3'));p.drawEllipse(QRectF(156,233,48,15))
            else:p.drawRoundedRect(QRectF(167,230,27,34),5,5)
        p.restore()
