import json
from datetime import datetime
from PySide6.QtCore import Qt, QDateTime, QThreadPool
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QPushButton,
    QPlainTextEdit, QLineEdit, QListWidget, QListWidgetItem, QDateTimeEdit, QComboBox,
    QFormLayout, QMessageBox, QFileDialog, QCheckBox)
from . import ai
from .workers import Job
from .activities import ActivitiesPage
from .accounts import AccountsPage

STYLE = '''
QWidget { font-family: 'Microsoft YaHei UI'; font-size: 14px; color: #233c55; }
QWidget#Panel { background: #f2f7fc; }
QTabWidget::pane { border: 0; background: #f2f7fc; }
QTabBar::tab { padding: 12px 17px; background: #e7eff7; border-radius: 7px; margin: 3px; }
QTabBar::tab:selected { background: #25597d; color: white; }
QPushButton { background: #27658e; color: white; border: 0; border-radius: 7px; padding: 9px 15px; }
QPushButton:disabled { background: #a9becd; }
QPushButton:hover { background: #367ba5; }
QLineEdit,QPlainTextEdit,QListWidget,QDateTimeEdit,QComboBox { background: white; border: 1px solid #ccdae6; border-radius: 6px; padding: 8px; }
QLabel#Title { font-size: 25px; font-weight: 600; }
'''


def button(text, fn, layout):
    b = QPushButton(text)
    b.clicked.connect(fn)
    layout.addWidget(b)
    return b


class Panel(QWidget):
    def __init__(self, store, pet, clock=None):
        super().__init__()
        self.store, self.pet = store, pet
        self.history, self.jobs = [], []
        self.setObjectName('Panel')
        self.setWindowTitle('知微 · 伴你知微见著')
        self.resize(720, 620)
        self.setMinimumSize(610, 510)
        self.setStyleSheet(STYLE)
        root = QVBoxLayout(self)
        title = QLabel('知微  /  桌面伙伴')
        title.setObjectName('Title')
        root.addWidget(title)
        root.addWidget(QLabel('灵感随手记，重要的事交给我提醒。'))
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.make_notes()
        self.make_reminders()
        self.make_chat()
        self.make_usage()
        self.make_settings()
        if clock:
            self.tabs.addTab(ActivitiesPage(store, clock, pet), '日常')
        self.tabs.addTab(AccountsPage(self), '账户告警')
        self.status = QLabel('离线功能已就绪 · 悬浮图标快捷操作，更多展开工作台')
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def page(self, name):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        self.tabs.addTab(page, name)
        return layout

    def show_page(self, index):
        self.tabs.setCurrentIndex(index)
        self.refresh_notes()
        self.refresh_reminders()
        self.refresh_usage()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def make_notes(self):
        layout = self.page('记事')
        self.note_input = QPlainTextEdit()
        self.note_input.setPlaceholderText('刚想到什么？先留在这里。笔记只保存在本机。')
        self.note_input.setMaximumHeight(100)
        layout.addWidget(self.note_input)
        row = QHBoxLayout()
        button('保存笔记', self.save_note, row)
        button('导出全部', self.export_notes, row)
        button('删除选中', self.delete_note, row)
        layout.addLayout(row)
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索笔记')
        self.search.textChanged.connect(self.refresh_notes)
        layout.addWidget(self.search)
        self.note_list = QListWidget()
        self.note_list.setWordWrap(True)
        self.note_list.itemDoubleClicked.connect(lambda item: QMessageBox.information(self, '笔记', item.data(Qt.UserRole + 1)))
        layout.addWidget(self.note_list)
        self.refresh_notes()

    def refresh_notes(self):
        self.note_list.clear()
        for row in self.store.notes(self.search.text()):
            item = QListWidgetItem(row['created'].replace('T', ' ') + '\n' + row['body'][:180])
            item.setData(Qt.UserRole, row['id'])
            item.setData(Qt.UserRole + 1, row['body'])
            self.note_list.addItem(item)

    def save_note(self):
        if not self.note_input.toPlainText().strip():
            return
        self.store.add_note(self.note_input.toPlainText())
        self.note_input.clear()
        self.refresh_notes()
        self.pet.react('happy', '记住啦，灵感不会溜走了。')
        self.status.setText('已保存在本机。')

    def delete_note(self):
        item = self.note_list.currentItem()
        if item and QMessageBox.question(self, '删除笔记', '删除这条笔记？') == QMessageBox.Yes:
            self.store.delete_note(item.data(Qt.UserRole))
            self.refresh_notes()

    def export_notes(self):
        path, _ = QFileDialog.getSaveFileName(self, '导出笔记', '知微笔记.json', 'JSON (*.json)')
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump([dict(r) for r in self.store.notes()], f, ensure_ascii=False, indent=2)
                self.status.setText('笔记已导出。')
            except OSError:
                self.status.setText('无法写入所选文件，请换一个位置。')

    def make_reminders(self):
        layout = self.page('提醒')
        self.reminder_title = QLineEdit()
        self.reminder_title.setPlaceholderText('例如：起身喝水 / 晚上整理素材')
        layout.addWidget(self.reminder_title)
        row = QHBoxLayout()
        self.due = QDateTimeEdit(QDateTime.currentDateTime().addSecs(300))
        self.due.setCalendarPopup(True)
        self.due.setDisplayFormat('yyyy-MM-dd HH:mm')
        self.repeat = QComboBox()
        self.repeat.addItems(['仅一次', '每天', '每周'])
        row.addWidget(self.due)
        row.addWidget(self.repeat)
        button('添加提醒', self.add_reminder, row)
        layout.addLayout(row)
        self.reminder_list = QListWidget()
        layout.addWidget(self.reminder_list)
        button('取消选中提醒', self.cancel_reminder, layout)
        hint = QLabel('到点会弹窗并提示；应用退出或电脑关机时不能响铃，下次打开会补报。\n关闭这个面板仍在托盘运行；右键桌宠选择“退出知微”才会退出。')
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def add_reminder(self):
        title = self.reminder_title.text().strip()
        if not title:
            self.status.setText('请填写提醒内容。')
            return
        due = self.due.dateTime().toPython()
        if due <= datetime.now():
            self.status.setText('请选择未来的提醒时间。')
            return
        self.store.add_reminder(title, due, ['once', 'daily', 'weekly'][self.repeat.currentIndex()])
        self.reminder_title.clear()
        self.refresh_reminders()
        self.pet.react('happy', '时间记好了，到点叫你。')

    def refresh_reminders(self):
        self.reminder_list.clear()
        labels = {'once': '一次', 'daily': '每天', 'weekly': '每周'}
        for r in self.store.reminders():
            item = QListWidgetItem(f"{r['due'].replace('T', ' ')} · {labels[r['repeat']]}\n{r['title']}" + (' · 待确认' if r['status'] == 'ringing' else ''))
            item.setData(Qt.UserRole, r['id'])
            self.reminder_list.addItem(item)

    def cancel_reminder(self):
        item = self.reminder_list.currentItem()
        if item:
            self.store.cancel_reminder(item.data(Qt.UserRole))
            self.refresh_reminders()

    def make_chat(self):
        layout = self.page('问知微')
        hint = QLabel('连接 AI 后可问答。仅发送本页最近的对话；不会自动上传笔记、账单或桌面内容。')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.chat_log = QPlainTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setPlaceholderText('还没有对话。可以先在“连接”中选择服务商。')
        layout.addWidget(self.chat_log)
        self.question = QPlainTextEdit()
        self.question.setMaximumHeight(85)
        self.question.setPlaceholderText('想问知微什么？')
        layout.addWidget(self.question)
        row = QHBoxLayout()
        self.send = button('发送', self.send_chat, row)
        self.clear_chat = button('清空对话', self.reset_chat, row)
        layout.addLayout(row)

    def reset_chat(self):
        self.history.clear()
        self.chat_log.clear()

    def config(self):
        return self.store.get('connection', {'provider': 'DeepSeek', **ai.PROVIDERS['DeepSeek']})

    def run_job(self, fn, done, failed):
        job = Job(fn)
        self.jobs.append(job)
        job.signals.done.connect(done)
        job.signals.failed.connect(failed)
        job.signals.done.connect(lambda _: self.jobs.remove(job))
        job.signals.failed.connect(lambda _: self.jobs.remove(job))
        QThreadPool.globalInstance().start(job)

    def send_chat(self):
        text = self.question.toPlainText().strip()
        if not text:
            return
        config = self.config().copy()
        history = self.history + [{'role': 'user', 'content': text}]
        self.send.setEnabled(False)
        self.clear_chat.setEnabled(False)
        self.pet.react('thinking', '让我想一想……', 80)
        self.status.setText('正在等待 AI 回答……')
        def finish():
            self.send.setEnabled(True)
            self.clear_chat.setEnabled(True)
            self.pet.react('idle')
        def done(result):
            finish()
            self.history = history + [{'role': 'assistant', 'content': result['text']}]
            self.chat_log.appendPlainText('你：' + text + '\n\n知微：' + result['text'] + '\n')
            self.question.clear()
            self.store.record_usage(config['provider'], config['model'], result['usage'], result['trace_id'])
            self.status.setText('已回复 · 对话仅在本次运行中保存')
        def failed(message):
            finish()
            self.status.setText(message + ' 输入内容已保留。')
        self.run_job(lambda: ai.chat(config, history), done, failed)

    def make_usage(self):
        layout = self.page('查账')
        self.balance_label = QLabel('官方余额：尚未查询')
        self.balance_label.setWordWrap(True)
        layout.addWidget(self.balance_label)
        self.balance_btn = button('查询当前连接余额', self.fetch_balance, layout)
        hint = QLabel('DeepSeek 使用官方余额接口。OpenAI / 兼容接口暂不提供余额查询。\n下方统计仅覆盖知微发出的请求，不代表整个账户，也不代表 ChatGPT 订阅额度。')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.usage_text = QPlainTextEdit()
        self.usage_text.setReadOnly(True)
        layout.addWidget(self.usage_text)
        button('刷新本地用量', self.refresh_usage, layout)

    def refresh_usage(self):
        rows = self.store.usage_summary()
        self.usage_text.setPlainText('\n\n'.join(f"{r['provider']} / {r['model']}\n请求 {r['calls']} 次 · 输入 {r['inputs']} tokens · 输出 {r['outputs']} tokens" for r in rows) or '暂无用量。连接 AI 并完成问答后会显示。')

    def fetch_balance(self):
        config = self.config().copy()
        self.balance_btn.setEnabled(False)
        self.balance_label.setText('正在向官方接口查询……')
        def done(data):
            self.balance_btn.setEnabled(True)
            lines = [f"{r['currency']} {r['total_balance']}（赠送 {r['granted_balance']}，充值 {r['topped_up_balance']}）" for r in data['balance_infos']]
            self.balance_label.setText(config['provider'] + ' 官方余额\n' + '\n'.join(lines) + '\n查询时间：' + datetime.now().strftime('%m-%d %H:%M:%S'))
        def failed(message):
            self.balance_btn.setEnabled(True)
            self.balance_label.setText(message)
        self.run_job(lambda: ai.balance(config), done, failed)

    def make_settings(self):
        layout = self.page('设置与连接')
        from . import startup
        self.startup_toggle = QCheckBox('开机启动（仅当前 Windows 用户）')
        self.startup_toggle.setChecked(startup.enabled())
        self.startup_toggle.toggled.connect(self.change_startup)
        layout.addWidget(self.startup_toggle)
        layout.addWidget(QLabel('首次启动默认开启；关闭后不会再次自动开启。移动程序目录后请重新开启。'))
        form = QFormLayout()
        self.provider = QComboBox()
        self.provider.addItems(list(ai.PROVIDERS))
        self.url, self.model, self.key = QLineEdit(), QLineEdit(), QLineEdit()
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText('留空保留原密钥；密钥保存在 Windows 凭据管理器')
        self.model.setPlaceholderText('填写账户实际可用的模型 ID')
        for title, widget in [('服务商', self.provider), ('接口地址', self.url), ('模型名称', self.model), ('API Key', self.key)]:
            form.addRow(title, widget)
        layout.addLayout(form)
        self.provider.currentTextChanged.connect(self.provider_changed)
        c = self.config()
        self.provider.setCurrentText(c['provider'])
        self.url.setText(c['url'])
        self.model.setText(c['model'])
        button('保存连接', self.save_connection, layout)
        button('移除当前连接密钥', self.remove_key, layout)
        hint = QLabel('不填写密钥也能使用记事、提醒和桌宠互动。\n兼容接口支持本地 localhost 服务。切换服务商不会自动发送任何内容。\nAI 回复不能操作电脑；提醒和记事请使用相应页面。')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch()

    def change_startup(self, value):
        from . import startup
        try:
            startup.set_enabled(value)
            self.store.set('startup_initialized', True)
            self.status.setText('开机启动已开启。' if value else '开机启动已关闭。')
        except OSError:
            self.startup_toggle.blockSignals(True)
            self.startup_toggle.setChecked(startup.enabled())
            self.startup_toggle.blockSignals(False)
            self.status.setText('无法修改开机启动，请检查当前用户权限。')

    def provider_changed(self, provider):
        c = self.store.get('provider_' + provider, ai.PROVIDERS[provider])
        self.url.setText(c['url'])
        self.model.setText(c['model'])
        self.key.clear()

    def save_connection(self):
        try:
            c = {'provider': self.provider.currentText(), 'url': ai.validate_url(self.url.text().strip()), 'model': self.model.text().strip()}
            if self.key.text().strip():
                ai.save_key(c['provider'], c['url'], self.key.text().strip())
            self.store.set('connection', c)
            self.store.set('provider_' + c['provider'], c)
            self.key.clear()
            self.status.setText('连接配置已保存。点击“发送”或“查询余额”才会联网。')
        except ai.AIError as e:
            self.status.setText(str(e))
        except Exception:
            self.status.setText('无法保存到 Windows 凭据管理器，未保存密钥。')

    def remove_key(self):
        try:
            ai.delete_key(self.provider.currentText(), self.url.text().strip())
            self.status.setText('当前连接的密钥已移除。')
        except Exception:
            self.status.setText('无法访问 Windows 凭据管理器。')
