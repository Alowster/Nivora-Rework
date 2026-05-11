from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QCursor

class RegionSelector(QWidget):
    region_selected = Signal(int, int, int, int)  # x, y, w, h (physical global coords)

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

        # Usar la pantalla donde está el cursor
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        self._dpr = screen.devicePixelRatio()
        # Offset lógico de esta pantalla en el escritorio virtual (para multi-monitor)
        self._screen_offset = screen.geometry().topLeft()

        self._screenshot = screen.grabWindow(0)
        self._screenshot.setDevicePixelRatio(self._dpr)

        # Mover la ventana a la pantalla correcta antes de showFullScreen
        self.move(screen.geometry().topLeft())
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
                # Coordenadas locales + offset de pantalla = globales lógicas
                # Globales lógicas * DPR = globales físicas (lo que necesita PIL)
                self.region_selected.emit(
                    int((self.selection.x() + self._screen_offset.x()) * self._dpr),
                    int((self.selection.y() + self._screen_offset.y()) * self._dpr),
                    int(self.selection.width() * self._dpr),
                    int(self.selection.height() * self._dpr)
                )
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
