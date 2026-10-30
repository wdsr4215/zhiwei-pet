"""上半身悬浮扇形入口，矢量图标与缓动展开。"""
import math
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QCursor, QRegion
from PySide6.QtWidgets import QWidget, QToolButton, QGraphicsOpacityEffect


class IconButton(QToolButton):
    def __init__(self, kind, label, parent):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(44, 44)
        self.setToolTip(label)
        self.setAccessibleName(label)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor('#a9d5e9'), 1))
        p.setBrush(QColor('#d9f4ff') if self.underMouse() else QColor(246, 252, 255, 245))
        p.drawEllipse(1, 1, 42, 42)
        p.setPen(QPen(QColor('#315b7a'), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        k = self.kind
        if k == 'note':
            p.drawRoundedRect(14, 12, 17, 21, 2, 2)
            for y in (18, 23, 28): p.drawLine(18, y, 27, y)
        elif k == 'chat':
            p.drawRoundedRect(11, 13, 23, 17, 5, 5)
            p.drawLine(16, 30, 14, 34)
            for x in (17, 23, 29): p.drawPoint(x, 22)
        elif k == 'clock':
            p.drawEllipse(12, 12, 21, 21)
            p.drawLine(22, 16, 22, 23); p.drawLine(22, 23, 28, 26)
        elif k == 'wallet':
            p.drawRoundedRect(11, 14, 23, 18, 3, 3)
            p.drawRect(25, 20, 9, 7); p.drawPoint(29, 23)
        elif k == 'play':
            p.drawEllipse(11, 15, 21, 16)
            p.drawLine(32, 23, 36, 18); p.drawLine(32, 23, 36, 28)
            p.drawPoint(17, 21)
        elif k == 'more':
            for x in (15,22,29): p.drawEllipse(x-1,21,2,2)
        else:
            p.drawLine(13, 18, 22, 27); p.drawLine(22, 27, 31, 18)


class HoverFan(QWidget):
    def __init__(self, pet):
        super().__init__(pet)
        self.pet = pet
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.progress = 0.0
        self.target = 0.0
        self.buttons = []
        actions = [(kind, label, lambda checked=False,k=kind: pet.quick_action.emit(k))
                   for kind,label in [('note','快速便签'),('clock','专注与提醒'),('chat','和知微聊天'),('wallet','账户小账本'),('play','一起玩')]]
        actions.append(('more','更多：展开完整工作台',lambda: pet.open_panel.emit(0)))
        for kind, label, action in actions:
            button = IconButton(kind, label, self)
            button.clicked.connect(action)
            button.clicked.connect(self.dismiss)
            self.buttons.append(button)
        self.hide()
        self.clock = QTimer(self)
        self.clock.setTimerType(Qt.PreciseTimer)
        self.clock.timeout.connect(self.step)
        self.clock.start(16)
        self.outside_ticks = 0

    def dismiss(self):
        self.target = 0.0

    def reveal(self):
        if self.pet.collapsed or self.pet.state in ('drag', 'fall'): return
        self.target = 1.0
        self.outside_ticks = 0
        self.setGeometry(0, 55, self.pet.width(), 170)
        self.show()
        self.raise_()
        self.pet.target_x = None
        if self.pet.state == 'walk': self.pet.state = 'idle'

    def step(self):
        if not self.isVisible(): return
        if self.pet.collapsed or self.pet.state in ('drag', 'fall'):
            self.hide(); self.progress = self.target = 0.0; return
        inside = self.pet.rect().contains(self.pet.mapFromGlobal(QCursor.pos()))
        self.outside_ticks = 0 if inside else self.outside_ticks + 1
        if self.outside_ticks > 20: self.target = 0.0
        self.progress += (self.target - self.progress) * .22
        if self.target == 0 and self.progress < .015:
            self.hide(); self.progress = 0; return
        radius = min(124, self.width() / 2 - 25) * self.progress
        region = QRegion()
        for i, button in enumerate(self.buttons):
            angle = math.radians(190 + i * 32)
            button.move(round(self.width()/2 + radius*math.cos(angle)-22),
                        round(140 + radius*math.sin(angle)-22))
            button.setEnabled(self.progress > .85)
            region = region.united(QRegion(button.geometry(), QRegion.Ellipse))
        self.setMask(region)
