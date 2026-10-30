"""声明式动作包；只读资源，不执行插件代码。"""
import json
from pathlib import Path
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt


class SpriteLibrary:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.animations = {}
        path = self.root / 'pack.json'
        if not path.exists():
            return
        manifest = json.loads(path.read_text(encoding='utf-8'))
        if manifest.get('schema') != 1:
            raise ValueError('不支持的动作包版本')
        for name, spec in manifest['animations'].items():
            source = (self.root / spec['file']).resolve()
            if not source.is_relative_to(self.root):
                raise ValueError('动作资源必须位于包目录内')
            sheet = QPixmap(str(source))
            if sheet.isNull():
                continue
            if 'rects' in spec:
                frames = []
                for x, y, w, h in spec['rects']:
                    if x < 0 or y < 0 or x + w > sheet.width() or y + h > sheet.height():
                        raise ValueError('动作帧超出图集边界')
                    canvas = QPixmap(spec['canvas'], spec['canvas'])
                    canvas.fill(Qt.transparent)
                    painter = QPainter(canvas)
                    painter.drawPixmap((spec['canvas'] - w) // 2, spec['canvas'] - h, sheet.copy(x, y, w, h))
                    painter.end()
                    frames.append(canvas)
            else:
                cols, rows = spec['columns'], spec['rows']
                w, h = sheet.width() // cols, sheet.height() // rows
                frames = [sheet.copy((i % cols) * w, (i // cols) * h, w, h) for i in spec['frames']]
            self.animations[name] = (frames, spec.get('fps', 8))
        self.specs = manifest['animations']

    def frame(self, name, elapsed):
        if name not in self.animations:
            return None
        frames, fps = self.animations[name]
        durations = self.specs[name].get('durations')
        if durations and len(durations) == len(frames):
            position = (elapsed * 1000) % sum(durations)
            for frame, duration in zip(frames, durations):
                if position < duration:
                    return frame
                position -= duration
        return frames[int(elapsed * fps) % len(frames)]
