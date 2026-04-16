from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen

class RegionSelector(QWidget):
    region_selected = Signal(int, int, int, int)  # x, y, w, h

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.origin = QPoint()
        self.selection = QRect()
        self.is_dragging = False

        self._screenshot = QApplication.primaryScreen().grabWindow(0)

        self.showFullScreen()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self._screenshot)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
        if not self.selection.isNull():
            painter.drawPixmap(self.selection, self._screenshot, self.selection)

            pen = QPen(QColor(255, 255, 255, 220), 1.5)
            painter.setPen(pen)
            painter.drawRect(self.selection)


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.position().toPoint()
            self.selection = QRect()
            self.is_dragging = True


    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.selection = QRect(self.origin, event.position().toPoint()).normalized()
            self.update()


    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            if self.selection.width() > 0 and self.selection.height() > 0:
                self.region_selected.emit(
                    self.selection.x(),
                    self.selection.y(),
                    self.selection.width(),
                    self.selection.height()
                )
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()