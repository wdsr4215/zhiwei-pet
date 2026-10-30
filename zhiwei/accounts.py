import time
from datetime import datetime
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QDoubleSpinBox, QSpinBox, QCheckBox)
from . import ai
from .codex_usage import read_limits, summarize


class AccountsPage(QWidget):
    def __init__(self, panel):
        super().__init__()
        self.panel, self.store = panel, panel.store
        self.busy = set()
        self.last_alert = {}
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('账户监测 · 余额、费用和订阅额度分别查看'))
        self.output = QLabel('尚未查询。无账户连接时，其余桌宠功能正常运行。')
        self.output.setWordWrap(True)
        layout.addWidget(self.output)
        row = QHBoxLayout()
        for name, callback in [('DeepSeek 余额', self.deepseek), ('Codex 额度', self.codex), ('OpenAI 月花费', self.openai)]:
            b = QPushButton(name)
            b.clicked.connect(callback)
            row.addWidget(b)
        layout.addLayout(row)
        self.admin_key = QLineEdit()
        self.admin_key.setEchoMode(QLineEdit.Password)
        self.admin_key.setPlaceholderText('可选：OpenAI Admin API Key（只用于官方组织费用查询）')
        layout.addWidget(self.admin_key)
        row = QHBoxLayout()
        save = QPushButton('保存账单专用密钥')
        save.clicked.connect(self.save_admin)
        row.addWidget(save)
        remove = QPushButton('移除账单密钥')
        remove.clicked.connect(self.remove_admin)
        row.addWidget(remove)
        layout.addLayout(row)
        self.watch_ds = QCheckBox('每 10 分钟检查 DeepSeek，余额不足提醒')
        self.watch_codex = QCheckBox('每 10 分钟检查本机 Codex，剩余额度过低提醒')
        self.watch_ds.setChecked(self.store.get('watch_ds', False))
        self.watch_codex.setChecked(self.store.get('watch_codex', False))
        self.ds_threshold = QDoubleSpinBox()
        self.ds_threshold.setRange(0, 100000)
        self.ds_threshold.setValue(self.store.get('ds_threshold', 10))
        self.ds_threshold.setSuffix('（按返回币种）')
        self.codex_threshold = QSpinBox()
        self.codex_threshold.setRange(1, 99)
        self.codex_threshold.setValue(self.store.get('codex_threshold', 15))
        self.codex_threshold.setSuffix('% 剩余')
        for check, threshold in [(self.watch_ds, self.ds_threshold), (self.watch_codex, self.codex_threshold)]:
            layout.addWidget(check)
            layout.addWidget(threshold)
        self.watch_ds.toggled.connect(lambda v: self.store.set('watch_ds', v))
        self.watch_codex.toggled.connect(lambda v: self.store.set('watch_codex', v))
        self.ds_threshold.valueChanged.connect(lambda v: self.store.set('ds_threshold', v))
        self.codex_threshold.valueChanged.connect(lambda v: self.store.set('codex_threshold', v))
        hint = QLabel('Codex 读取本机已登录官方客户端的额度，不是 ChatGPT 全产品余额，也不消耗重置次数。\nOpenAI 月花费来自组织 Costs API，需要 Admin Key；它不是剩余充值余额。\n监测默认关闭，同类告警最多每 6 小时一次。')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(600000)

    def call(self, name, fn, done):
        if name in self.busy:
            return
        self.busy.add(name)
        self.output.setText(name + ' 查询中……')
        def success(data):
            self.busy.discard(name)
            done(data)
        def fail(message):
            self.busy.discard(name)
            self.output.setText(name + '：' + message)
        self.panel.run_job(fn, success, fail)

    def alert(self, ident, message):
        if time.time() - self.last_alert.get(ident, 0) >= 21600:
            self.last_alert[ident] = time.time()
            self.store.add_reminder(message, datetime.now())

    def deepseek(self):
        config = self.store.get('provider_DeepSeek', {'url': ai.PROVIDERS['DeepSeek']['url'], 'model': ai.PROVIDERS['DeepSeek']['model']})
        config = {**config, 'provider': 'DeepSeek'}
        def done(data):
            self.output.setText('DeepSeek 官方余额：\n' + '\n'.join(r['currency'] + ' ' + r['total_balance'] for r in data['balance_infos']))
            if self.watch_ds.isChecked():
                for r in data['balance_infos']:
                    if float(r['total_balance']) < self.ds_threshold.value():
                        self.alert('ds_' + r['currency'], f"DeepSeek 余额剩余 {r['currency']} {r['total_balance']}，低于你设置的阈值。")
        self.call('DeepSeek', lambda: ai.balance(config), done)

    def codex(self):
        def done(data):
            rows = summarize(data)
            lines = []
            for r in rows:
                reset = datetime.fromtimestamp(r['reset']).strftime('%m-%d %H:%M') if r['reset'] else '未知'
                lines.append(f"{r['name']} · {r['minutes']} 分钟窗口 · 剩余 {r['remaining']}% · 重置 {reset}")
                if self.watch_codex.isChecked() and r['remaining'] < self.codex_threshold.value():
                    self.alert('codex_' + r['name'], f"Codex {r['name']} 额度剩余 {r['remaining']}%，注意安排用量。")
            self.output.setText('\n'.join(lines) or '没有可用的 Codex 额度数据。')
        self.call('Codex', read_limits, done)

    def openai(self):
        self.call('OpenAI', ai.openai_monthly_costs, lambda totals: self.output.setText('OpenAI 本月组织累计费用（UTC 月界限）：\n' + ('\n'.join(k + ' ' + v for k, v in totals.items()) or '暂无费用记录')))

    def save_admin(self):
        if self.admin_key.text().strip():
            try:
                ai.save_key('OpenAI Admin', 'https://api.openai.com/v1', self.admin_key.text().strip())
                self.admin_key.clear()
                self.output.setText('账单专用密钥已保存在 Windows 凭据管理器。')
            except Exception:
                self.output.setText('密钥保存失败，请检查 Windows 凭据管理器。')

    def remove_admin(self):
        try:
            ai.delete_key('OpenAI Admin', 'https://api.openai.com/v1')
            self.output.setText('账单专用密钥已移除。')
        except Exception:
            self.output.setText('无法访问凭据管理器。')

    def poll(self):
        if self.watch_ds.isChecked():
            self.deepseek()
        if self.watch_codex.isChecked():
            self.codex()
