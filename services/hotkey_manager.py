from __future__ import annotations

import logging
import time
import threading

from PySide6.QtCore import QObject, Signal

import keyboard

from data.database import get_all_macros


log = logging.getLogger(__name__)

_FOCUS_DELAY = 0.15


class HotkeyManager(QObject):
    shell_requested = Signal(dict)

    def __init__(self):
        super().__init__()
        self._handles = []

    def reload(self):
        self._unregister_all()
        for macro in get_all_macros():
            hotkey = (macro.get("hotkey") or "").strip()
            if not hotkey:
                continue
            try:
                handle = keyboard.add_hotkey(
                    hotkey,
                    self._make_callback(macro),
                    suppress=True,
                )
                self._handles.append(handle)
            except Exception as e:
                log.warning("No se pudo registrar hotkey %r: %s", hotkey, e)

    def _make_callback(self, macro):
        if macro["type"] == "text":
            content = macro["content"]

            def _write():
                time.sleep(_FOCUS_DELAY)
                try:
                    keyboard.write(content, delay=0.01)
                except Exception as e:
                    log.warning("Error al escribir texto de macro: %s", e)

            return lambda: threading.Thread(target=_write, daemon=True).start()
        else:
            return lambda: self.shell_requested.emit(macro)

    def _unregister_all(self):
        for h in self._handles:
            try:
                keyboard.remove_hotkey(h)
            except Exception:
                pass
        self._handles.clear()

    def shutdown(self):
        self._unregister_all()
