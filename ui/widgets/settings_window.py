import config

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                               QApplication, QSlider)
from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath


class SettingsWindow(QFrame):
    opacity_changed = Signal(float)   # 0.0 – 1.0
    scale_changed = Signal(float)     # factor pill
    box_scale_changed = Signal(float) # factor box

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
        self.setFixedSize(230, 270)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(0)

        title = QLabel("Ajustes")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setProperty("class", "SectionLabel")
        layout.addWidget(title)

        layout.addSpacing(16)

        # ── Opacidad ──────────────────────────────────────────────
        opacity_desc = QLabel("Opacidad de la ventana")
        opacity_desc.setProperty("class", "SettingsDesc")
        layout.addWidget(opacity_desc)

        layout.addSpacing(6)

        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(8)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setProperty("class", "SettingsSlider")
        opacity_row.addWidget(self.opacity_slider)

        self._opacity_val = QLabel("100%")
        self._opacity_val.setFixedWidth(34)
        self._opacity_val.setProperty("class", "SettingsValue")
        opacity_row.addWidget(self._opacity_val)

        layout.addLayout(opacity_row)

        layout.addSpacing(20)

        # ── Tamaño UI ─────────────────────────────────────────────
        size_desc = QLabel("Tamaño de la interfaz")
        size_desc.setProperty("class", "SettingsDesc")
        layout.addWidget(size_desc)

        layout.addSpacing(6)

        size_row = QHBoxLayout()
        size_row.setSpacing(8)

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(85, 150)
        self.size_slider.setValue(100)
        self.size_slider.setProperty("class", "SettingsSlider")
        size_row.addWidget(self.size_slider)

        self._size_val = QLabel("100%")
        self._size_val.setFixedWidth(34)
        self._size_val.setProperty("class", "SettingsValue")
        size_row.addWidget(self._size_val)

        layout.addLayout(size_row)

        layout.addSpacing(20)

        # ── Tamaño box ────────────────────────────────────────────
        box_desc = QLabel("Tamaño de la ventana")
        box_desc.setProperty("class", "SettingsDesc")
        layout.addWidget(box_desc)

        layout.addSpacing(6)

        box_row = QHBoxLayout()
        box_row.setSpacing(8)

        self.box_slider = QSlider(Qt.Orientation.Horizontal)
        self.box_slider.setRange(85, 150)
        self.box_slider.setValue(100)
        self.box_slider.setProperty("class", "SettingsSlider")
        box_row.addWidget(self.box_slider)

        self._box_val = QLabel("100%")
        self._box_val.setFixedWidth(34)
        self._box_val.setProperty("class", "SettingsValue")
        box_row.addWidget(self._box_val)

        layout.addLayout(box_row)

        layout.addStretch()

        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.size_slider.valueChanged.connect(self._on_scale_changed)
        self.box_slider.valueChanged.connect(self._on_box_scale_changed)

        QApplication.instance().focusWindowChanged.connect(self._on_focus_changed)
        QApplication.instance().installEventFilter(self)

    def _on_opacity_changed(self, value):
        self._opacity_val.setText(f"{value}%")
        self.opacity_changed.emit(value / 100.0)

    def _on_scale_changed(self, value):
        self._size_val.setText(f"{value}%")
        self.scale_changed.emit(value / 100.0)

    def _on_box_scale_changed(self, value):
        self._box_val.setText(f"{value}%")
        self.box_scale_changed.emit(value / 100.0)

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
        path.addRoundedRect(rect, 20, 20)

        painter.setBrush(QBrush(QColor(*config.BACKGROUND_COLOR)))
        painter.setPen(QPen(QColor(*config.BORDER_COLOR), 1.5))
        painter.drawPath(path)
