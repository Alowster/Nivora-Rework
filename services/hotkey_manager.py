from __future__ import annotations

import logging
import time
import threading
from typing import Callable

import keyboard

from data.database import get_all_macros

log = logging.getLogger(__name__)

_FOCUS_DELAY = 0.15


class HotkeyManager:
    """Registra hotkeys globales definidas en la DB de macros (sin dependencias Qt)."""

    def __init__(self, on_shell_macro: Callable[[dict], None] | None = None):
        self._on_shell_macro = on_shell_macro or (lambda m: None)
        self._handles: list = []

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

    def _make_callback(self, macro: dict) -> Callable:
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
            return lambda: self._on_shell_macro(macro)

    def _unregister_all(self):
        for h in self._handles:
            try:
                keyboard.remove_hotkey(h)
            except Exception:
                pass
        self._handles.clear()

    def shutdown(self):
        self._unregister_all()
