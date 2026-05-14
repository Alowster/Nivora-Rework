from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QSize, Qt
import config

def create_svg_icon(svg_content, size=None):
    if size is None:
        size = config.ICON_SIZE
    svg_bytes = QByteArray(svg_content.encode())
    renderer = QSvgRenderer(svg_bytes)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

def create_icon_button(svg_content, style_class, name, callback=None):
    button = QPushButton()
    button.setFixedSize(config.BUTTON_SIZE, config.BUTTON_SIZE)
    button.setProperty("class", style_class)
    button.setCursor(Qt.CursorShape.PointingHandCursor)

    icon = create_svg_icon(svg_content)
    button.setIcon(icon)
    button.setIconSize(QSize(config.ICON_SIZE, config.ICON_SIZE))

    if callback:
        button.clicked.connect(lambda: callback(name))

    return button
