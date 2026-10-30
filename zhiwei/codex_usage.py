"""可选官方客户端桥：只读额度 RPC，不打开任务、不执行工具、不读取令牌文件。"""
import json
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from .ai import AIError


def read_limits(executable=None):
    executable = executable or shutil.which('codex')
    if not executable and os.name == 'nt':
        # 官方桌面客户端的版本化安装目录；不扫描用户文件或凭据。
        candidates = list((Path(os.environ.get('LOCALAPPDATA', '')) / 'OpenAI/Codex/bin').glob('*/codex.exe'))
        if candidates:
            executable = str(max(candidates, key=lambda p: p.stat().st_mtime))
    if not executable:
        raise AIError('未找到 Codex 客户端。可安装并登录后查询；桌宠本身不依赖它。')
    proc = subprocess.Popen([executable, 'app-server', '--listen', 'stdio://'], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    messages = queue.Queue()
    def reader():
        for line in proc.stdout:
            try:
                messages.put(json.loads(line))
            except ValueError:
                continue
    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    def send(payload):
        proc.stdin.write(json.dumps(payload) + '\n')
        proc.stdin.flush()
    def receive(ident):
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            try:
                msg = messages.get(timeout=min(1, max(.01, deadline - time.monotonic())))
            except queue.Empty:
                if proc.poll() is not None:
                    raise AIError('Codex 客户端已退出，请检查本机安装。')
                continue
            if msg.get('id') == ident:
                if 'error' in msg:
                    raise AIError('Codex 暂不能读取额度，请确认已在官方客户端登录。')
                return msg.get('result', {})
        raise AIError('读取 Codex 额度超时；不会重试登录或使用重置次数。')
    try:
        send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'zhiwei_pet', 'version': '0.2.0'},
            'capabilities': {'explicitGatewayOauth': True}}})
        receive(1)
        send({'method': 'initialized'})
        send({'id': 2, 'method': 'account/rateLimits/read', 'params': {'excludeResetCreditDetails': True}})
        return receive(2)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def summarize(data):
    buckets = data.get('rateLimitsByLimitId') or {'codex': data.get('rateLimits')}
    result = []
    for name, bucket in buckets.items():
        if not bucket:
            continue
        for period in ('primary', 'secondary'):
            window = bucket.get(period)
            if window and window.get('usedPercent') is not None:
                result.append({'name': name, 'minutes': window.get('windowDurationMins'),
                    'remaining': max(0, min(100, 100 - window['usedPercent'])), 'reset': window.get('resetsAt')})
    return result
