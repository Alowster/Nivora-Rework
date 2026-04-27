from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QLabel, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer, QEvent, Signal
from PySide6.QtGui import QKeySequence
from data.database import get_all_macros, create_macro, update_macro_hotkey, delete_macro
import subprocess

class HotkeyCapture(QLineEdit):
    confirmed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPlaceholderText("Click para asignar...")
        self._capturing = False

    def mousePressEvent(self, event):
        self._capturing = True
        self.setText("")
        self.setPlaceholderText("Pulsa la combinación...")
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if not self._capturing:
            return

        key = event.key()

