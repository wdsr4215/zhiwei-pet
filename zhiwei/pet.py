"""透明桌宠。呼吸/摆动绘制参考 dafeiyu-pet (MIT)，见 licenses。"""
import math
import random
import time
from PySide6.QtCore import Qt, QTimer, QRectF, Signal, QPropertyAnimation, QPoint, QEasingCurve
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont, QPen
from PySide6.QtWidgets import QWidget, QMenu, QApplication
from .sprites import SpriteLibrary
from .voice import Voice
from .hover_fan import HoverFan
from .companion import CompanionRoutine
from .swing import swing_projection
from .docking import nearby_edge, snap_position, dream_bubbles


class Pet(QWidget):
    open_panel = Signal(int)
    quick_action = Signal(str)
    quit_requested = Signal()
    STATES = {'idle': '陪伴', 'happy': '开心', 'thinking': '思考中', 'remind': '有提醒', 'sleep': '休息', 'drag': '被提起',
              'walk': '散步', 'eat': '吃饭', 'drink': '喝水', 'play': '找小鲸玩', 'peek': '悄悄看看', 'fall': '落地中', 'docked': '摸鱼做梦', 'tired': '歇一小会', 'swing': '荡秋千', 'daydream': '放空一下'}

    def __init__(self, image, store):
        super().__init__()
        self.store = store
        self.setWindowTitle('知微 · 桌面伙伴')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.pix = QPixmap(str(image))
        self.sprites = SpriteLibrary(image.parent / 'sprites')
        self.voice = Voice(image.parent / 'voice', store)
        if self.pix.isNull():
            raise RuntimeError('缺少角色图片 assets/character.png')
        self.dock_side = None
        self.dock_pix = QPixmap(str(image.parent / 'sprites' / 'dock-rest.png'))
        self.state = 'idle'
        self.until = 0
        self.state_started = time.monotonic()
        self.next_idle = time.monotonic() + random.uniform(15, 30)
        self.target_x = None
        self.facing = 1
        self.collapsed = False
        self.last_edge = None
        self.edge_check = 0
        self.fall_velocity = 0
        self.pending_notice = None
        self.quick_active = lambda: False
        self.text = '我是知微。双击我，记下一点灵感吧。'
        self.text_until = time.monotonic() + 12
        self.drag_origin = None
        self.start_pos = None
        self.resize_pet(store.get('pet_size', 290))
        screen = QApplication.primaryScreen().availableGeometry()
        pos = store.get('position', [screen.right() - self.width() - 40, screen.bottom() - self.height() - 20])
        self.move(*pos)
        self.keep_on_screen()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.last_tick = time.monotonic()
        self.walk_fraction = 0.0
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.start(16)
        self.fan = HoverFan(self)
        self.routine = CompanionRoutine(self)
        self.peek_left = True
        self.peek_animation = QPropertyAnimation(self, b'pos', self)
        self.peek_animation.setEasingCurve(QEasingCurve.InOutSine)
        self.setMouseTracking(True)
        side = store.get('dock_side')
        if side in ('left','right','top','bottom'):
            self.dock(side)

    def resize_pet(self, height):
        self.art_height = height
        self.setFixedSize(max(250, height + 24), height + 110)
        self.store.set('pet_size', height)
        self.update()

    def keep_on_screen(self):
        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        r = screen.availableGeometry()
        self.move(max(r.left(), min(self.x(), r.right() - self.width() + 1)),
                  max(r.top(), min(self.y(), r.bottom() - self.height() + 1)))

    def react(self, state, text='', duration=4, speak=True):
        if self.dock_side:
            return
        self.state, self.until = state, time.monotonic() + duration
        self.state_started = time.monotonic()
        self.target_x = None
        if speak:
            self.voice.play(state)
        elif not text:
            self.text_until = 0
        if text:
            self.text, self.text_until = text, time.monotonic() + max(duration, 5)
        self.update()

    def tick(self):
        now = time.monotonic()
        dt = min(.05, now - self.last_tick)
        self.last_tick = now
        if self.dock_side and self.state != 'drag':
            self.state = 'docked'
            self.target_x = None
            self.update()
            return
        if now > self.edge_check:
            from .window_edge import foreground_edge
            self.last_edge = foreground_edge() or self.last_edge
            self.edge_check = now + 2
        if self.state == 'fall':
            screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
            floor = screen.availableGeometry().bottom() - self.height() + 1
            self.fall_velocity = min(26, self.fall_velocity + 45 * dt)
            self.move(self.x(), min(floor, self.y() + round(self.fall_velocity * dt * 30)))
            if self.y() >= floor:
                self.react('idle', duration=2, speak=False)
        elif self.state == 'walk' and self.target_x is not None:
            dx = self.target_x - self.x()
            self.facing = 1 if dx >= 0 else -1
            if abs(dx) <= 3:
                self.state, self.target_x = 'idle', None
            else:
                self.walk_fraction += 60 * dt
                step = int(self.walk_fraction)
                self.walk_fraction -= step
                self.move(self.x() + self.facing * min(step, abs(dx)), self.y())
        elif self.state not in ('idle', 'sleep', 'drag') and now > self.until:
            self.state = 'idle'
            self.fall_velocity = 0
        if self.pending_notice and self.state not in ('drag', 'fall'):
            kind, text = self.pending_notice
            self.pending_notice = None
            self.notify(kind, text)
        self.routine.tick(now)
        self.update()

    def notify(self, kind, text):
        if self.dock_side:
            return  # 提醒仍由 ReminderPresenter 弹窗；角色不说话、不离开边缘。
        self.text, self.text_until = text, time.monotonic() + 15
        if self.state in ('drag', 'fall'):
            self.pending_notice = kind, text
            return
        state = {'water': 'drink', 'focus': 'happy', 'movement': 'happy'}.get(kind, 'remind')
        self.react(state, text, 12)

    def set_quiet(self, enabled):
        self.store.set('quiet', enabled)
        if enabled:
            self.voice.player.stop()

    def set_voice_enabled(self, enabled):
        self.store.set('voice_enabled', enabled)
        if not enabled:
            self.voice.player.stop()

    def walk(self):
        self.undock()
        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        r = screen.availableGeometry()
        self.react('walk', duration=20)
        distance = random.randint(45,110)
        direction = random.choice([-1,1])
        target = max(r.left(),min(self.x()+direction*distance,r.right()-self.width()+1))
        if abs(target-self.x())<40:
            target=max(r.left(),min(self.x()-direction*distance,r.right()-self.width()+1))
        self.target_x=target

    def collapse(self):
        self.collapsed = not self.collapsed
        self.target_x = None
        if self.collapsed:
            self.setFixedSize(90, 110)
        else:
            self.resize_pet(self.store.get('pet_size', 290))
        self.keep_on_screen()

    def nearby_window_side(self):
        from .window_edge import foreground_edge
        edge=foreground_edge()
        if not edge:
            return None
        x,y,w,h=edge
        center=self.frameGeometry().center()
        if not y <= center.y() <= y+h:
            return None
        distances={'left':abs(center.x()-x),'right':abs(center.x()-(x+w))}
        side=min(distances,key=distances.get)
        return side if distances[side] <= self.width()*.55 else None

    def can_peek_nearby(self):
        return self.nearby_window_side() is not None

    def peek(self, automatic=False):
        self.undock()
        side=self.nearby_window_side()
        if side:
            self.facing=1 if side=='left' else -1
            self.react('peek','' if automatic else '我就在这里悄悄看看。',18,speak=False)
        else:
            self.react('daydream','' if automatic else '窗边有点远，我就在这里陪你。',35,speak=False)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        t = time.monotonic()
        if not self.dock_side and not self.collapsed and (t < self.text_until or self.state in ('thinking', 'remind')):
            p.setPen(QColor('#bed9ec'))
            p.setBrush(QColor(248, 253, 255, 245))
            p.drawRoundedRect(QRectF(7, 5, self.width() - 14, 68), 16, 16)
            p.setPen(QColor('#27435d'))
            p.setFont(QFont('Microsoft YaHei UI', 10))
            p.drawText(QRectF(18, 10, self.width() - 36, 57), Qt.AlignCenter | Qt.TextWordWrap, self.text)
        breath = 1 + .006 * math.sin(t * (1.1 if self.state in ('sleep','docked') else 2.2))
        frame = self.sprites.frame('sleep' if self.state == 'tired' else 'drag' if self.state == 'fall' else self.state, t - self.state_started)
        if (self.dock_side and self.state != 'drag') or self.state in ('swing','daydream'):
            frame = self.dock_pix if not self.dock_pix.isNull() else self.sprites.frame('sleep', 0)
        if frame is None:
            frame = self.sprites.frame('idle', t) or self.pix
        h = (88 if self.collapsed else self.art_height) * breath
        w = h * frame.width() / frame.height()
        if w > self.width() - 8:
            h *= (self.width() - 8) / w
            w = self.width() - 8
        bob = -abs(math.sin(t * 5)) * 9 if self.state == 'happy' else math.sin(t * 2) * 2
        p.save()
        if self.state == 'swing':
            scale,rise=swing_projection(t-self.state_started)
            center=self.width()/2
            seat_y=self.height()-38-h*.42-rise
            p.setPen(QPen(QColor('#a5bcdf'),2))
            for side in (-1,1):
                p.drawLine(QPoint(round(center+side*w*.28),85),
                           QPoint(round(center+side*w*.28*scale),round(seat_y)))
            p.translate(center,seat_y)
            p.scale(scale,scale)
            p.setPen(QPen(QColor('#728eb9'),5,Qt.SolidLine,Qt.RoundCap))
            p.drawLine(QPoint(round(-w*.31),0),QPoint(round(w*.31),0))
            p.translate(0,h*.42)
            bob=0
        else:
            p.translate(self.width() / 2, self.height() - 19)
        if self.facing < 0:
            p.scale(-1, 1)
        if self.state != 'swing':
            p.rotate(math.sin(t * 6) * 3 if self.state == 'drag' else math.sin(t * 1.7) * .5)
        p.setOpacity(.72 if self.state == 'sleep' else 1)
        p.drawPixmap(QRectF(-w / 2, -h + bob, w, h), frame, QRectF(frame.rect()))
        p.restore()
        if (self.dock_side or self.state == 'daydream') and self.state != 'drag' and not self.collapsed:
            dream_bubbles(p,self.width(),self.height(),t-self.state_started)
        p.setBrush(QColor(246, 251, 255, 230))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(self.width() / 2 - 67, self.height() - 22, 134, 21), 10, 10)
        p.setPen(QColor('#315b7a'))
        p.setFont(QFont('Microsoft YaHei UI', 8))
        p.drawText(QRectF(0, self.height() - 22, self.width(), 21), Qt.AlignCenter, '知微' if self.collapsed else '知微  ·  ' + self.STATES[self.state])

    def dock(self, side):
        self.peek_animation.stop()
        self.dock_side = side
        self.state = 'docked'
        self.state_started = time.monotonic()
        self.target_x = None
        self.pending_notice = None
        self.text_until = 0
        self.voice.player.stop()
        self.fan.dismiss()
        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        self.move(*snap_position(self.geometry(), screen.availableGeometry(), side))
        self.store.set('dock_side', side)
        self.store.set('position', [self.x(),self.y()])
        self.update()

    def undock(self):
        if self.dock_side is None:
            return
        self.dock_side = None
        self.store.set('dock_side', None)
        self.state = 'idle'
        self.state_started = time.monotonic()
        self.next_idle = time.monotonic() + 3
        self.routine.resume(15)
        self.text_until = 0

    def enterEvent(self, e):
        self.fan.reveal()
        super().enterEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.peek_animation.stop()
            self.drag_origin, self.start_pos = e.globalPosition().toPoint(), self.pos()

    def mouseMoveEvent(self, e):
        if self.drag_origin is not None:
            delta = e.globalPosition().toPoint() - self.drag_origin
            if delta.manhattanLength() > 5:
                self.fan.dismiss()
                self.state = 'drag'
                self.move(self.start_pos + delta)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.drag_origin is not None:
            moved = (e.globalPosition().toPoint() - self.drag_origin).manhattanLength() > 5
            self.drag_origin = None
            self.keep_on_screen()
            self.store.set('position', [self.x(), self.y()])
            if moved:
                screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
                side = nearby_edge(self.geometry(), screen.availableGeometry())
                if side:
                    self.dock(side)
                    return
                self.undock()
                self.routine.resume(15)
            if self.dock_side:
                self.state = 'docked'
                return
            self.react('happy', '轻一点呀，我又不是行李。' if moved else random.choice([
                '嗯？又发现什么有趣的事了？', '灵感会游走，先记下来吧。', '哼，我才不是只会吃白饭呢。']))
            if moved and not self.collapsed:
                self.state = 'fall'
                self.fall_velocity = 0

    def mouseDoubleClickEvent(self, e):
        if self.collapsed:
            self.collapse()
        else:
            self.quick_action.emit('chat')

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        for kind, label in [('note','快速便签'),('clock','专注与提醒'),('chat','和知微聊天'),('wallet','账户小账本')]:
            menu.addAction(label, lambda checked=False,k=kind: self.quick_action.emit(k))
        menu.addAction('更多：展开完整工作台', lambda: self.open_panel.emit(0))
        menu.addSeparator()
        play = menu.addMenu('一起玩')
        for state, label, line in [('eat', '喂一碗白米饭', '白米饭！再给小鲸留一口。'), ('drink', '一起喝水', '你也喝一口嘛。'), ('play', '找小鲸玩', '来，碰一下手心！'), ('happy', '击掌', '接住啦！')]:
            play.addAction(label, lambda checked=False, s=state, t=line: self.react(s, t, 9))
        play.addAction('出去散步', self.walk)
        play.addAction('趴在窗边偷看', self.peek)
        roam = menu.addAction('自由散步')
        roam.setCheckable(True)
        roam.setChecked(self.store.get('roam', True))
        roam.toggled.connect(lambda value: self.store.set('roam', value))
        quiet = menu.addAction('安静模式')
        quiet.setCheckable(True)
        quiet.setChecked(self.store.get('quiet', False))
        quiet.toggled.connect(self.set_quiet)
        voice = menu.addAction('角色语音')
        voice.setCheckable(True)
        voice.setChecked(self.store.get('voice_enabled', True))
        voice.toggled.connect(self.set_voice_enabled)
        menu.addAction('展开' if self.collapsed else '收起成小伙伴', self.collapse)
        if self.dock_side:
            menu.addAction('结束摸鱼', self.undock)
        menu.addAction('休息 / 唤醒', lambda: self.react('idle' if self.state == 'sleep' else 'sleep', '我在这里陪着你。'))
        sizes = menu.addMenu('角色大小')
        for label, size in [('小', 220), ('中', 290), ('大', 370)]:
            sizes.addAction(label, lambda checked=False, s=size: (self.resize_pet(s), self.keep_on_screen()))
        menu.addAction('退出知微', self.quit_requested.emit)
        menu.exec(e.globalPos())
