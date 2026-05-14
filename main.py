import sys
import os
import config
from data.database import init_db
from ui.widgets.island_bar import IslandWindow
from PySide6.QtWidgets import QApplication

try:
    from services.hotkey_manager import HotkeyManager
except Exception:
    HotkeyManager = None

def main():
    """Función principal de la aplicación"""
    init_db()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    style_path = os.path.join(os.path.dirname(__file__), config.STYLES_FILE)
    if os.path.exists(style_path):
        with open(style_path, 'r') as f:
            app.setStyleSheet(f.read())

    window = IslandWindow()


    hotkeys = None
    if HotkeyManager is not None:
        try:
            hotkeys = HotkeyManager()
            hotkeys.shell_requested.connect(window.macros_content._ejecutar)
            hotkeys.reload()
            window.macros_content.macros_changed.connect(hotkeys.reload)
        except Exception as e:
            print(f"No se pudieron registrar hotkeys globales: {e}")
            hotkeys = None

    app.aboutToQuit.connect(lambda: hotkeys.shutdown() if hotkeys else None)

    window.show()

    print("Aplicación Island iniciada")

    sys.exit(app.exec())

if __name__ == '__main__':
    main()