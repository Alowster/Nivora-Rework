import config

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath

class PopupPanel(QFrame):
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
        self.setFixedSize(329, 450)
        self.setProperty("class", "PopupPanel")

        self.status_dot = QLabel()
        self.status_dot.setFixedSize(8, 8)
        self.status_dot.setProperty("class", "StatusDot--active")

        self._current_content = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def set_status(self, estado):
        self.status_dot.setProperty("class", f"StatusDot--{estado}")
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)

    def set_content(self, widget):
        if self._current_content is widget:
            return
        if self._current_content is not None:
            self._layout.removeWidget(self._current_content)
            self._current_content.hide()
        self._current_content = widget
        self._layout.addWidget(widget)
        widget.show()

    def _calc_pos(self, anchor_widget):
        anchor_rect = anchor_widget.rect()
        cx = anchor_widget.mapToGlobal(anchor_rect.center()).x()
        by = anchor_widget.mapToGlobal(anchor_rect.bottomLeft()).y()
        return cx - self.width() // 2, by

    def show_below(self, anchor_widget):
        x, y = self._calc_pos(anchor_widget)
        self.move(x, y)
        self.show()

    def reposition(self, anchor_widget):
        x, y = self._calc_pos(anchor_widget)
        self.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        radius = 25
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        painter.setBrush(QBrush(QColor(*config.BACKGROUND_COLOR)))
        painter.setPen(QPen(QColor(*config.BORDER_COLOR), 1.5))
        painter.drawPath(path)