import time
from datetime import datetime, timedelta
from PySide6.QtCore import QTimer, Signal, QObject
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QSpinBox, QCheckBox)
from PySide6.QtCore import Qt


class ActivityClock(QObject):
    notify = Signal(str, str)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

    def start_focus(self, minutes):
        self.store.set('focus', {'end': time.time() + minutes * 60, 'minutes': minutes})

    def stop_focus(self):
        self.store.set('focus', None)

    def tick(self):
        focus = self.store.get('focus')
        if focus and time.time() >= focus['end']:
            self.stop_focus()
            self.notify.emit('focus', f"专注 {focus['minutes']} 分钟完成啦，起来伸个懒腰吧。")
        for kind, title in [('water', '喝几口水吧，小鲸也在等你休息呢。'),
                            ('movement', '到了你设置的活动时间：起身走走，或做一组舒适的提肛练习。')]:
            c = self.store.get('habit_' + kind)
            if c and c.get('enabled') and time.time() >= c['next']:
                c['next'] = time.time() + c['minutes'] * 60
                self.store.set('habit_' + kind, c)
                self.notify.emit(kind, title)


class ActivitiesPage(QWidget):
    def __init__(self, store, clock, pet):
        super().__init__()
        self.store, self.clock, self.pet = store, clock, pet
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('小事有着落，专注有节奏'))
        row = QHBoxLayout()
        self.todo = QLineEdit()
        self.todo.setPlaceholderText('添加一个小目标')
        row.addWidget(self.todo)
        add = QPushButton('添加待办')
        add.clicked.connect(self.add_task)
        row.addWidget(add)
        layout.addLayout(row)
        self.tasks = QListWidget()
        self.tasks.itemChanged.connect(self.toggle_task)
        layout.addWidget(self.tasks)
        self.refresh_tasks()
        row = QHBoxLayout()
        self.minutes = QSpinBox()
        self.minutes.setRange(1, 180)
        self.minutes.setValue(25)
        self.minutes.setSuffix(' 分钟')
        row.addWidget(self.minutes)
        start = QPushButton('开始专注')
        start.clicked.connect(lambda: self.clock.start_focus(self.minutes.value()))
        row.addWidget(start)
        stop = QPushButton('结束计时')
        stop.clicked.connect(clock.stop_focus)
        row.addWidget(stop)
        layout.addLayout(row)
        self.countdown = QLabel('还没有开始专注')
        layout.addWidget(self.countdown)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        for kind, label, default in [('water', '喝水提醒', 45), ('movement', '活动 / 提肛提醒', 60)]:
            c = store.get('habit_' + kind, {'enabled': False, 'minutes': default})
            row = QHBoxLayout()
            check = QCheckBox(label)
            check.setChecked(c['enabled'])
            minutes = QSpinBox()
            minutes.setRange(5, 240)
            minutes.setValue(c['minutes'])
            minutes.setSuffix(' 分钟一次')
            row.addWidget(check)
            row.addWidget(minutes)
            def update(_, k=kind, cb=check, sb=minutes):
                self.store.set('habit_' + k, {'enabled': cb.isChecked(), 'minutes': sb.value(), 'next': time.time() + sb.value() * 60})
            check.toggled.connect(update)
            minutes.valueChanged.connect(update)
            layout.addLayout(row)
        layout.addWidget(QLabel('习惯提醒默认关闭，由你选择；休息期间可以右键桌宠进入安静模式。'))

    def refresh_tasks(self):
        self.tasks.blockSignals(True)
        self.tasks.clear()
        for i, task in enumerate(self.store.get('tasks', [])):
            item = QListWidgetItem(task['title'])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if task['done'] else Qt.Unchecked)
            item.setData(Qt.UserRole, i)
            self.tasks.addItem(item)
        self.tasks.blockSignals(False)

    def add_task(self):
        if not self.todo.text().strip():
            return
        tasks = self.store.get('tasks', [])
        tasks.append({'title': self.todo.text().strip(), 'done': False})
        self.store.set('tasks', tasks)
        self.todo.clear()
        self.refresh_tasks()

    def toggle_task(self, item):
        tasks = self.store.get('tasks', [])
        task = tasks[item.data(Qt.UserRole)]
        task['done'] = item.checkState() == Qt.Checked
        self.store.set('tasks', tasks)
        if task['done']:
            self.pet.react('happy', '又完成一件事，击掌！')

    def update_clock(self):
        c = self.store.get('focus')
        if c:
            remain = max(0, int(c['end'] - time.time()))
            self.countdown.setText(f'专注中  {remain // 60:02d}:{remain % 60:02d}  · 我会安静陪着你')
        else:
            self.countdown.setText('还没有开始专注')
