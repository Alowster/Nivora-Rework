import sys
import os
import logging
import config
import translations
from data.database import init_db
from ui.widgets.island_bar import IslandWindow
from PySide6.QtWidgets import QApplication

log = logging.getLogger(__name__)


def main():
    """Función principal de la aplicación"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        from services.hotkey_manager import HotkeyManager
    except Exception as _hk_err:
        log.error("No se pudo importar HotkeyManager: %s", _hk_err, exc_info=True)
        HotkeyManager = None

    translations.load_language()

    try:
        init_db()
    except Exception:
        log.exception("No se pudo inicializar la base de datos")
        raise

    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)
    qt_app.setStyle("Fusion")

    style_path = os.path.join(os.path.dirname(__file__), config.STYLES_FILE)
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            qt_app.setStyleSheet(f.read())

    window = IslandWindow()

    hotkeys = None
    if HotkeyManager is not None:
        try:
            hotkeys = HotkeyManager()
            hotkeys.shell_requested.connect(window.macros_content._ejecutar)
            hotkeys.reload()
            window.macros_content.macros_changed.connect(hotkeys.reload)
        except Exception as e:
            log.error("No se pudieron registrar hotkeys globales: %s", e, exc_info=True)
            hotkeys = None

    def shutdown_hotkeys():
        if hotkeys:
            try:
                hotkeys.shutdown()
            except Exception:
                log.exception("Error cerrando hotkeys globales")

    qt_app.aboutToQuit.connect(shutdown_hotkeys)

    window.show()
    log.info("Aplicación Island iniciada")
    return qt_app.exec()


if __name__ == "__main__":
    sys.exit(main())