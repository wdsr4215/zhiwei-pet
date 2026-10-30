"""手动拖靠屏幕工作区边缘，安静休息与梦泡泡。"""
import math
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPen
from .pet_theme import whale


def nearby_edge(rect, area, threshold=30):
    distances={'left':abs(rect.left()-area.left()),'right':abs(rect.right()-area.right()),
               'top':abs(rect.top()-area.top()),'bottom':abs(rect.bottom()-area.bottom())}
    edge=min(distances,key=distances.get)
    return edge if distances[edge]<=threshold else None


def snap_position(rect, area, side):
    x=max(area.left(),min(rect.x(),area.right()-rect.width()+1))
    y=max(area.top(),min(rect.y(),area.bottom()-rect.height()+1))
    if side=='left': x=area.left()
    elif side=='right': x=area.right()-rect.width()+1
    elif side=='top': y=area.top()
    elif side=='bottom': y=area.bottom()-rect.height()+1
    return x,y


def dream_bubbles(p,width,height,elapsed):
    # 有间隔的三颗泡泡，连续上浮淡出；没有文本或声音。
    p.save()
    for i in range(3):
        phase=(elapsed-i*1.6)%8
        if phase>5: continue
        u=phase/5
        opacity=math.sin(math.pi*u)*.6
        radius=5+u*15
        x=width*.7+math.sin(phase*.7+i)*9
        y=height*.43-u*height*.28
        p.setOpacity(opacity);p.setPen(QPen(QColor('#accff2'),1.2));p.setBrush(QColor(239,248,255,135))
        p.drawEllipse(QRectF(x-radius,y-radius,radius*2,radius*2))
        p.setPen(QPen(QColor('#ffffff'),1.7));p.drawArc(QRectF(x-radius+3,y-radius+3,radius*2-6,radius*2-6),55*16,65*16)
        if i==1 and radius>12: whale(p,x,y,.35)
    p.restore()
