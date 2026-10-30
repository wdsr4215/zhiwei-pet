"""知微的珍珠白、星海蓝交互皮肤，矢量小物图标。"""
import math
from PySide6.QtCore import Qt, QRectF, QPointF, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter,QPainterPath,QColor,QPen,QLinearGradient,QFont,QPolygonF
from PySide6.QtWidgets import QPushButton

STYLE = '''
QWidget {font-family:'Microsoft YaHei UI';font-size:13px;color:#29466c;}
QLabel#Heading {font-size:19px;font-weight:600;color:#243e73;}
QLabel#Caption {font-size:11px;color:#7084a2;}
QLabel#Status {font-size:12px;color:#687e9e;}
QPushButton {background:#e7edfb;color:#385081;border:1px solid #d3dff1;border-radius:15px;padding:10px 16px;min-height:18px;}
QPushButton:hover {background:#dae7ff;border:1px solid #a5bde6;}
QPushButton:pressed {background:#cbdcff;}
QPushButton:focus {border:2px solid #96aed8;}
QPushButton:disabled {color:#8c9ab1;background:#edf0f6;}
QPushButton#Primary {background:#4765a1;color:white;border:1px solid #4765a1;}
QPushButton#Primary:hover {background:#5678b7;}
QPushButton#Close {border:0;background:#e9eef9;border-radius:14px;padding:0;font-size:18px;color:#7588aa;}
QLineEdit,QPlainTextEdit,QSpinBox {selection-background-color:#ccdcf7;background:#ffffff;border:1px solid #dce5f3;border-radius:14px;padding:11px;color:#344e75;}
QLineEdit:focus,QPlainTextEdit:focus,QSpinBox:focus {border:1px solid #9ebbe7;background:#fcfdff;}
QScrollBar:vertical {width:6px;background:transparent;}
QScrollBar::handle:vertical {background:#c4d4eb;border-radius:3px;min-height:22px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
'''

def whale(p,x,y,size=1):
    p.save();p.translate(x,y);p.scale(size,size)
    p.setPen(Qt.NoPen);p.setBrush(QColor('#536fae'))
    p.drawEllipse(QRectF(-22,-12,43,27))
    tail=QPainterPath();tail.moveTo(15,0);tail.cubicTo(24,-20,35,-15,30,-5);tail.quadTo(25,2,18,7);tail.closeSubpath();p.drawPath(tail)
    p.setBrush(QColor('#eaf4ff'));p.drawEllipse(QRectF(-19,2,34,12))
    p.setBrush(QColor('#263b69'));p.drawEllipse(QRectF(-12,-3,3,4))
    p.setBrush(QColor('#c3dafa'));p.drawEllipse(QRectF(-16,3,5,3));p.restore()

def paint_shell(widget):
    p=QPainter(widget);p.setRenderHint(QPainter.Antialiasing)
    r=QRectF(7,7,widget.width()-14,widget.height()-14)
    p.setPen(Qt.NoPen);p.setBrush(QColor(45,67,109,22));p.drawRoundedRect(r.translated(0,3),25,25)
    gradient=QLinearGradient(0,0,widget.width(),widget.height());gradient.setColorAt(0,QColor('#f8fbff'));gradient.setColorAt(1,QColor('#eef1ff'))
    p.setBrush(gradient);p.setPen(QPen(QColor('#cad8ef'),1));p.drawRoundedRect(r,25,25)
    p.save();clip=QPainterPath();clip.addRoundedRect(r,25,25);p.setClipPath(clip)
    wave=QPainterPath();y=widget.height()-27;wave.moveTo(0,y);wave.cubicTo(widget.width()*.3,y-18,widget.width()*.6,y+12,widget.width(),y-6);wave.lineTo(widget.width(),widget.height());wave.lineTo(0,widget.height());p.setPen(Qt.NoPen);p.setBrush(QColor('#e1eafa'));p.drawPath(wave);p.restore()
    whale(p,39,40,.55)
    p.setPen(QPen(QColor('#d5bc85'),1.2));p.drawLine(widget.width()-71,29,widget.width()-71,37);p.drawLine(widget.width()-75,33,widget.width()-67,33)

class PlayTile(QPushButton):
    def __init__(self,kind,title,subtitle,parent=None):
        super().__init__(parent);self.kind=kind;self.title=title;self.subtitle=subtitle
        self.setAccessibleName(title);self.setToolTip(subtitle);self.setCursor(Qt.PointingHandCursor);self.setObjectName('PlayTile');self.setStyleSheet('QPushButton#PlayTile {min-height:96px;max-height:96px;padding:0px;border:0px;}');self.setFixedHeight(96)
    def sizeHint(self):
        return QSize(136,96)
    def minimumSizeHint(self):
        return QSize(120,96)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        r=QRectF(2,2,self.width()-4,self.height()-4)
        p.setPen(QPen(QColor('#aec7eb' if self.underMouse() or self.hasFocus() else '#dce5f4'),1))
        p.setBrush(QColor('#e7efff' if self.isDown() else '#f0f5ff' if self.underMouse() else '#ffffff'));p.drawRoundedRect(r,18,18)
        p.save();p.translate(self.width()/2,27);p.setPen(QPen(QColor('#536fae'),1.8,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(QColor('#e5edfc'))
        k=self.kind
        if k=='play': whale(p,0,0,.65)
        elif k=='eat':
            p.drawArc(QRectF(-15,-5,30,24),180*16,180*16);p.drawLine(-15,7,15,7);p.drawLine(-5,19,5,19)
            p.setBrush(QColor('#f8faff'));p.drawEllipse(QRectF(-12,-7,24,13));p.drawLine(-14,7,14,7)
        elif k=='drink':
            p.drawRoundedRect(QRectF(-11,-10,20,27),4,4);p.drawArc(QRectF(7,-6,12,16),-90*16,180*16);p.drawLine(-7,3,5,3)
        elif k=='sleep':
            p.drawEllipse(QRectF(-13,-12,26,26));p.setPen(Qt.NoPen);p.setBrush(QColor('#ffffff'));p.drawEllipse(QRectF(-4,-17,24,24))
        elif k=='walk':
            p.drawEllipse(QRectF(-13,-10,9,15));p.drawEllipse(QRectF(4,0,9,15));p.drawEllipse(QRectF(-12,-17,5,5));p.drawEllipse(QRectF(5,-7,5,5))
        elif k=='swing':
            p.drawLine(-11,-13,-11,12);p.drawLine(11,-13,11,12);p.drawLine(-16,12,16,12);p.drawLine(-16,-13,16,-13)
        elif k=='daydream':
            for x,y,r in [(-8,8,4),(2,-2,6),(11,-12,4)]:p.drawEllipse(QRectF(x-r,y-r,r*2,r*2))
        elif k=='peek':
            p.drawRoundedRect(QRectF(-14,-12,28,26),3,3);p.drawLine(0,-12,0,14);p.drawLine(-14,1,14,1)
        p.restore();p.setPen(QColor('#324d7b'));p.setFont(QFont('Microsoft YaHei UI',10,QFont.DemiBold));p.drawText(QRectF(3,49,self.width()-6,20),Qt.AlignCenter,self.title)
        p.setPen(QColor('#8797b1'));p.setFont(QFont('Microsoft YaHei UI',8));p.drawText(QRectF(3,70,self.width()-6,17),Qt.AlignCenter,self.subtitle)
