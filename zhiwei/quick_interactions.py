"""围绕角色的独立能力交互，不打开工作台。"""
import time
from datetime import datetime, timedelta
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QPlainTextEdit, QLineEdit, QSpinBox, QApplication, QGridLayout)
from . import ai
from .pet_theme import STYLE, PlayTile, paint_shell


class QuickInteraction(QDialog):
    def __init__(self, pet, panel, clock, kind):
        super().__init__(pet, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.pet, self.panel, self.clock, self.store = pet, panel, clock, pet.store
        self.kind = kind
        self.setFixedWidth(340 if kind != 'chat' else 390)
        self.setObjectName('Quick')
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(STYLE)
        self.root = QVBoxLayout(self); self.root.setContentsMargins(24,24,24,30); self.root.setSpacing(12)
        header = QHBoxLayout(); header.setContentsMargins(35,0,0,0)
        heading=QLabel({'note':'拾起一点灵感', 'chat':'知微在听呢', 'clock':'陪你慢慢完成', 'wallet':'小鲸管家', 'play':'今天，陪我玩吧'}[kind]); heading.setObjectName('Heading')
        header.addWidget(heading); header.addStretch()
        close = QPushButton('×'); close.setObjectName('Close'); close.setFixedSize(28,28); close.setAccessibleName('关闭'); close.clicked.connect(self.hide)
        header.addWidget(close); self.root.addLayout(header)
        caption=QLabel({'note':'写下来，就不会游走啦。','chat':'悄悄话，也可以认真听。','clock':'一小步，也值得一声夸奖。','wallet':'用量与余额，替你分清楚。','play':'白米饭和你，我都很喜欢。'}[kind]);caption.setObjectName('Caption');self.root.addWidget(caption)
        getattr(self, 'make_' + kind)()
        self.status = QLabel(''); self.status.setObjectName('Status'); self.status.setWordWrap(True); self.root.addWidget(self.status)

    def paintEvent(self, event):
        paint_shell(self)

    def action(self, label, fn):
        b = QPushButton(label); b.setCursor(Qt.PointingHandCursor); b.setObjectName('Primary'); b.clicked.connect(fn); self.root.addWidget(b); return b

    def present(self):
        self.adjustSize()
        r = (QApplication.screenAt(self.pet.frameGeometry().center()) or QApplication.primaryScreen()).availableGeometry()
        x = self.pet.x()-self.width()-10
        if x < r.left(): x = self.pet.x()+self.pet.width()+10
        self.move(max(r.left(), min(x, r.right()-self.width()+1)), max(r.top(), min(self.pet.y()+65, r.bottom()-self.height()+1)))
        self.show(); self.raise_(); self.activateWindow()

    def make_note(self):
        self.input = QPlainTextEdit(); self.input.setPlaceholderText('这一刻想到的事……'); self.input.setFixedHeight(130)
        self.root.addWidget(self.input); self.action('收好这张便签', self.save_note)

    def save_note(self):
        text = self.input.toPlainText().strip()
        if not text: self.status.setText('先写一点内容吧。'); return
        self.store.add_note(text); self.input.clear(); self.status.setText('已保存在本机。')
        self.pet.react('happy', '我收好啦。')

    def make_chat(self):
        self.history = []
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setFixedHeight(200); self.log.setPlaceholderText('我在听。只发送这里的对话，不读取桌面。')
        self.root.addWidget(self.log)
        self.input = QLineEdit(); self.input.setPlaceholderText('想说什么？'); self.root.addWidget(self.input)
        self.send = self.action('说给知微听', self.chat); self.input.returnPressed.connect(self.chat)

    def chat(self):
        text = self.input.text().strip()
        if not text or not self.send.isEnabled(): return
        config = self.panel.config().copy(); history = self.history[-20:]+[{'role':'user','content':text}]
        self.send.setEnabled(False); self.status.setText('知微正在想……'); self.pet.react('thinking', duration=80)
        def done(result):
            self.history = history+[{'role':'assistant','content':result['text']}]
            self.log.appendPlainText('你：'+text+'\n知微：'+result['text']+'\n'); self.input.clear()
            self.store.record_usage(config['provider'], config['model'], result['usage'], result['trace_id'])
            self.send.setEnabled(True); self.status.setText(''); self.pet.react('idle')
        def failed(message):
            self.send.setEnabled(True); self.status.setText(message+' 可从“更多→连接”设置。'); self.pet.react('idle')
        self.panel.run_job(lambda: ai.chat(config, history), done, failed)

    def make_clock(self):
        self.count = QLabel(); self.count.setStyleSheet('font-size:34px;color:#29746b;'); self.root.addWidget(self.count)
        self.minutes = QSpinBox(); self.minutes.setRange(1,180); self.minutes.setValue(25); self.minutes.setSuffix(' 分钟'); self.root.addWidget(self.minutes)
        self.action('开始专注', lambda: self.clock.start_focus(self.minutes.value()))
        self.action('停止计时', self.clock.stop_focus)
        self.input = QLineEdit(); self.input.setPlaceholderText('也可以写一件稍后提醒的事'); self.root.addWidget(self.input)
        self.action('按上面的分钟数提醒我', self.remind)
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_count); self.timer.start(1000); self.update_count()

    def update_count(self):
        focus = self.store.get('focus')
        seconds = max(0, int(focus['end']-time.time())) if focus else 0
        self.count.setText(f'{seconds//60:02d}:{seconds%60:02d}' if focus else '准备好了吗？')

    def remind(self):
        text = self.input.text().strip()
        if not text: self.status.setText('请先填写提醒内容。'); return
        self.store.add_reminder(text, datetime.now()+timedelta(minutes=self.minutes.value()))
        self.input.clear(); self.status.setText('记好了，到点叫你。')

    def make_wallet(self):
        self.amount = QLabel('尚未查询'); self.amount.setWordWrap(True); self.amount.setStyleSheet('font-size:20px;'); self.root.addWidget(self.amount)
        self.root.addWidget(QLabel('官方余额与本地用量分别展示。'))
        self.query = self.action('查询当前连接余额', self.balance)
        local = QPlainTextEdit(); local.setReadOnly(True); local.setFixedHeight(110)
        local.setPlainText('\n'.join(f"{r['provider']}：{r['calls']} 次请求，{r['inputs']+r['outputs']} tokens" for r in self.store.usage_summary()) or '知微本地暂无用量'); self.root.addWidget(local)

    def balance(self):
        config = self.panel.config().copy(); self.query.setEnabled(False); self.amount.setText('查询中……')
        def done(data):
            self.query.setEnabled(True); self.amount.setText('\n'.join(f"{r['currency']} {r['total_balance']}" for r in data['balance_infos']))
            self.status.setText('官方余额 · '+datetime.now().strftime('%H:%M:%S'))
        def failed(message):
            self.query.setEnabled(True); self.amount.setText('未取得余额'); self.status.setText(message)
        self.panel.run_job(lambda: ai.balance(config), done, failed)

    def make_play(self):
        grid=QGridLayout(); grid.setSpacing(9); self.root.addLayout(grid)
        entries=[('eat','投喂白米饭','就一小碗嘛',lambda:self.pet.react('eat',duration=8)),
                 ('drink','碰杯喝水','你也喝一口',lambda:self.pet.react('drink',duration=8)),
                 ('play','找小鲸玩','碰一下手心',lambda:self.pet.react('play',duration=8)),
                 ('sleep','打个小盹','陪在你身边',lambda:self.pet.react('sleep',duration=8)),
                 ('swing','荡一会秋千','小鲸轻轻推',lambda:self.pet.react('swing',duration=90)),
                 ('daydream','一起发会呆','让思绪冒泡泡',lambda:self.pet.react('daydream',duration=60)),
                 ('walk','出去溜达','走走也很好',self.pet.walk),
                 ('peek','趴窗边看看','只看，不捣乱',self.pet.peek)]
        for index,(kind,title,subtitle,fn) in enumerate(entries):
            tile=PlayTile(kind,title,subtitle,self)
            tile.clicked.connect(lambda checked=False,action=fn:(self.pet.undock(),action()));tile.clicked.connect(self.hide);grid.addWidget(tile,index//2,index%2)
        fold=QPushButton('收进口袋里');fold.setCursor(Qt.PointingHandCursor);fold.clicked.connect(self.pet.collapse);fold.clicked.connect(self.hide);self.root.addWidget(fold)


class QuickInteractions:
    def __init__(self, pet, panel, clock):
        self.pet, self.panel, self.clock = pet, panel, clock
        self.windows = {}
        pet.quick_active = lambda: any(w.isVisible() for w in self.windows.values())

    def open(self, kind):
        for window in self.windows.values(): window.hide()
        if kind not in self.windows:
            self.windows[kind] = QuickInteraction(self.pet,self.panel,self.clock,kind)
        self.windows[kind].present()
