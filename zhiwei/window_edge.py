"""为窗边动作缓存前台窗口几何；不取标题、内容或文件。"""
import ctypes
import os
from ctypes import wintypes


def foreground_edge():
    if os.name != 'nt':
        return None
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.GetForegroundWindow.restype = wintypes.HWND
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    handle = user.GetForegroundWindow()
    pid = wintypes.DWORD()
    user.GetWindowThreadProcessId(handle, ctypes.byref(pid))
    if pid.value == os.getpid():
        return None
    rect = wintypes.RECT()
    if user.GetWindowRect(handle, ctypes.byref(rect)) and rect.right - rect.left > 150:
        return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
    return None
