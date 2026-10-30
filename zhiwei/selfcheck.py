"""独立包自检：临时数据库和内置资源，不调用付费接口或修改用户数据。"""
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from PySide6.QtCore import QTimer, QEventLoop, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from .storage import Store
from .sprites import SpriteLibrary
from .pet import Pet
from .panel import Panel
from .activities import ActivityClock


def run(root, destination):
    checks = {}
    try:
        with tempfile.TemporaryDirectory(prefix='zhiwei-check-') as temp:
            store = Store(Path(temp) / 'test.db')
            store.set('quiet', True)
            store.add_note('独立包验收')
            checks['note_persistence'] = store.notes()[0]['body'] == '独立包验收'
            store.add_reminder('验收提醒', datetime.now() - timedelta(seconds=1))
            checks['overdue_reminder'] = len(store.due_reminders()) == 1
            library = SpriteLibrary(root / 'assets/sprites')
            checks['animation_states'] = sorted(library.animations)
            checks['frame_count'] = sum(len(frames) for frames, _ in library.animations.values())
            pet = Pet(root / 'assets/character.png', store)
            clock = ActivityClock(store)
            panel = Panel(store, pet, clock)
            checks['workbench_tabs'] = panel.tabs.count()
            pet.collapse()
            checks['collapse'] = pet.collapsed and pet.width() == 90
            pet.collapse()
            checks['expand'] = not pet.collapsed and pet.width() > 90
            checks['audio'] = {}
            for path in (root / 'assets/voice').glob('*.mp3'):
                player = QMediaPlayer()
                loop = QEventLoop()
                player.durationChanged.connect(lambda _: loop.quit())
                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(loop.quit)
                player.setSource(QUrl.fromLocalFile(str(path)))
                timer.start(4000)
                loop.exec()
                timer.stop()
                checks['audio'][path.name] = player.duration()
                player.setSource(QUrl())
            pet.timer.stop()
            clock.timer.stop()
            for timer in panel.findChildren(QTimer):
                timer.stop()
            panel.close()
            pet.close()
            store.db.close()
        checks['passed'] = (checks['note_persistence'] and checks['overdue_reminder'] and checks['frame_count'] == 36
            and checks['workbench_tabs'] == 7 and checks['collapse'] and checks['expand']
            and len(checks['audio']) == 3 and all(n > 0 for n in checks['audio'].values()))
    except Exception as e:
        checks['passed'] = False
        checks['error'] = type(e).__name__ + ': ' + str(e)
    Path(destination).write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if checks['passed'] else 1
