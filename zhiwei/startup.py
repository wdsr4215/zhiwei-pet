"""当前用户开机启动；只管理本应用的 Run 值，不需要管理员权限。"""
import os
import subprocess
import sys
from pathlib import Path

KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME = 'ZhiweiPet'


def command():
    exe = Path(sys.executable)
    if getattr(sys, 'frozen', False):
        args = [str(exe), '--autostart']
    else:
        windowless = exe.with_name('pythonw.exe')
        args = [str(windowless if windowless.exists() else exe),
                str(Path(__file__).resolve().parent.parent / 'main.py'), '--autostart']
    return subprocess.list2cmdline(args)


def enabled():
    if os.name != 'nt':
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as key:
            value, _ = winreg.QueryValueEx(key, NAME)
            return value == command()
    except FileNotFoundError:
        return False


def set_enabled(value):
    if os.name != 'nt':
        raise OSError('开机启动目前仅支持 Windows。')
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY) as key:
        if value:
            winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ, command())
        else:
            try:
                winreg.DeleteValue(key, NAME)
            except FileNotFoundError:
                pass


def initialize(store):
    """首次安装默认开启；后续不覆盖用户在系统中关闭的选择。"""
    if store.get('startup_initialized', False):
        return False, ''
    try:
        set_enabled(True)
    except OSError as exc:
        return True, '未能设置开机启动，可在设置中重新开启：' + str(exc)
    store.set('startup_initialized', True)
    return True, '开机启动已默认开启，可随时在“设置与连接”中关闭。'
