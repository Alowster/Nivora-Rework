import config

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QApplication
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath


class SettingsWindow(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedSize(200, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        lbl = QLabel("Ajustes")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setProperty("class", "SectionLabel")
        layout.addWidget(lbl)
        layout.addStretch()

        QApplication.instance().focusWindowChanged.connect(self._on_focus_changed)
        QApplication.instance().installEventFilter(self)

    def _on_focus_changed(self, focused_window):
        if self.isVisible() and focused_window != self.windowHandle():
            self.hide()

    def eventFilter(self, obj, event):
        if self.isVisible() and event.type() == QEvent.Type.MouseButtonPress:
            pos = event.globalPosition().toPoint()
            if not self.geometry().contains(pos):
                self.hide()
        return super().eventFilter(obj, event)

    def show_right_of(self, anchor_widget):
        geo = anchor_widget.frameGeometry()
        x = geo.right() + 8
        y = geo.top()
        self.move(x, y)
        self.show()
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, 25, 25)

        painter.setBrush(QBrush(QColor(*config.BACKGROUND_COLOR)))
        painter.setPen(QPen(QColor(*config.BORDER_COLOR), 1.5))
        painter.drawPath(path)
