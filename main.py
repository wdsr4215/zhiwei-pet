import sys
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QTimer, Qt
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from zhiwei.storage import Store
from zhiwei.pet import Pet
from zhiwei.panel import Panel
from zhiwei.activities import ActivityClock
from zhiwei.notifications import ReminderPresenter
from zhiwei.quick_interactions import QuickInteractions


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('知微桌宠')
    app.setQuitOnLastWindowClosed(False)
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    if '--self-test' in sys.argv:
        from zhiwei.selfcheck import run
        return run(root, sys.argv[sys.argv.index('--self-test') + 1])
    socket = QLocalSocket()
    socket.connectToServer('ZhiweiPet-v1')
    if socket.waitForConnected(350):
        socket.write(b'open')
        socket.waitForBytesWritten(350)
        return 0
    QLocalServer.removeServer('ZhiweiPet-v1')
    server = QLocalServer()
    if not server.listen('ZhiweiPet-v1'):
        QMessageBox.warning(None, '知微', '无法启动本地单实例服务。')
        return 1
    image = root / 'assets' / 'character.png'
    app.setWindowIcon(QIcon(str(image)))
    store = Store()
    from zhiwei import startup
    first_start, startup_message = startup.initialize(store)
    pet = Pet(image, store)
    clock = ActivityClock(store)
    panel = Panel(store, pet, clock)
    pet.open_panel.connect(panel.show_page)
    quick = QuickInteractions(pet, panel, clock)
    pet.quick_action.connect(quick.open)
    pet.quit_requested.connect(app.quit)
    def second_instance():
        connection = server.nextPendingConnection()
        panel.show_page(0)
        connection.disconnectFromServer()
    server.newConnection.connect(second_instance)
    tray = QSystemTrayIcon(QIcon(str(image)), app)
    tray.setToolTip('知微 · 双击打开工作台')
    menu = QMenu()
    menu.addAction('打开知微', lambda: panel.show_page(0))
    menu.addAction('显示 / 隐藏桌宠', lambda: pet.setVisible(not pet.isVisible()))
    menu.addAction('退出', app.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: panel.show_page(0) if reason == QSystemTrayIcon.DoubleClick else None)
    tray.show()
    def activity_notice(kind, message):
        store.add_reminder(message, datetime.now(), kind=kind)
    clock.notify.connect(activity_notice)
    reminders = ReminderPresenter(store, pet, panel, tray, app.beep)
    timer = QTimer()
    timer.timeout.connect(reminders.tick)
    timer.start(1000)
    pet.show()
    if first_start or '--show' in sys.argv:
        panel.show_page(0)
    if first_start:
        panel.status.setText(startup_message)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
