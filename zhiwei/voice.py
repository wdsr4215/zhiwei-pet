import time
from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class Voice:
    def __init__(self, root, store):
        self.root, self.store = root, store
        self.player = QMediaPlayer()
        self.output = QAudioOutput()
        self.output.setVolume(.55)
        self.player.setAudioOutput(self.output)
        self.last = 0

    def play(self, state):
        if self.store.get('quiet', False) or not self.store.get('voice_enabled', True):
            return
        if time.monotonic() - self.last < 12:
            return
        name = {'eat': 'eat', 'thinking': 'think', 'happy': 'happy'}.get(state)
        if name and (self.root / (name + '.mp3')).exists():
            self.player.setSource(QUrl.fromLocalFile(str(self.root / (name + '.mp3'))))
            self.player.play()
            self.last = time.monotonic()
