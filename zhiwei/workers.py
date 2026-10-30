from PySide6.QtCore import QObject, Signal, QRunnable


class Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


class Job(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = Signals()

    def run(self):
        from .ai import AIError
        try:
            self.signals.done.emit(self.fn())
        except AIError as e:
            self.signals.failed.emit(str(e))
        except Exception:
            self.signals.failed.emit('操作失败，请检查网络和连接设置。密钥不会写入日志。')
