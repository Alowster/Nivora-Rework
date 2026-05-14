import sys
import os
import subprocess
import config
from PySide6.QtWidgets import (QApplication, QWidget, QPushButton,
                               QHBoxLayout, QGraphicsDropShadowEffect,
                               QMenu, QSystemTrayIcon)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush, QPainterPath,
                           QIcon)
from ui.widgets.popup_panel import PopupPanel
from ui.widgets.settings_window import SettingsWindow
from ui.panels.chat_panel import ChatPanel
from ui.panels.history_panel import HistoryPanel
from ui.panels.macros_panel import MacrosPanel
from data.database import init_db
from ui.widgets.icon_button import create_icon_button, create_svg_icon
from assets import icons

class IslandWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.drag_position = QPoint()
        self.initUI()

    def initUI(self):
        """Inicializa la interfaz de usuario"""
        # Configuración de la ventana
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Tamaño de la ventana desde config
        self.setFixedSize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

        # Posicionar en la parte superior central
        self.center_window()

        # Layout principal
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(
            config.LAYOUT_MARGIN_HORIZONTAL,
            config.LAYOUT_MARGIN_VERTICAL,
            config.LAYOUT_MARGIN_HORIZONTAL,
            config.LAYOUT_MARGIN_VERTICAL
        )
        main_layout.setSpacing(config.BUTTON_SPACING)

        self.main_layout = main_layout

        # Crear botones con iconos
        self._icon_svgs = [icons.get_chat_icon(), icons.get_clock_icon(), icons.get_sparkles_icon()]
        self.button1 = create_icon_button(self._icon_svgs[0], "GradientButton", "chat", self.on_button_clicked)
        self.button2 = create_icon_button(self._icon_svgs[1], "OutlineButton", "lista", self.on_button_clicked)
        self.button3 = create_icon_button(self._icon_svgs[2], "OutlineButton", "macros", self.on_button_clicked)

        main_layout.addWidget(self.button1)
        main_layout.addWidget(self.button2)
        main_layout.addWidget(self.button3)

        # Espaciador
        main_layout.addSpacing(10)

        # Botón de menú
        self.menu_button = self.create_menu_button()
        main_layout.addWidget(self.menu_button)

        self.setLayout(main_layout)
        self.setProperty("class", "IslandPill")

        # Panel popup compartido y contenidos
        self.popup = PopupPanel()
        self.settings = SettingsWindow()
        self.settings.opacity_changed.connect(self._apply_opacity)
        self.settings.scale_changed.connect(self._apply_scale)

        # Valores base para el escalado
        self._base_window_width = config.WINDOW_WIDTH
        self._base_window_height = config.WINDOW_HEIGHT
        self._base_button_size = config.BUTTON_SIZE
        self._base_icon_size = config.ICON_SIZE
        self._base_menu_button_width = config.MENU_BUTTON_WIDTH
        self._base_margin_h = config.LAYOUT_MARGIN_HORIZONTAL
        self._base_margin_v = config.LAYOUT_MARGIN_VERTICAL
        self._base_spacing = config.BUTTON_SPACING
        self.chat_content = ChatPanel()
        self.lista_content = HistoryPanel()
        self.macros_content = MacrosPanel()
        self.macros_content.macro_triggered.connect(self._on_macro_texto)

        self._content_map = {
            "chat": (self.chat_content, self.button1),
            "lista": (self.lista_content, self.button2),
            "macros": (self.macros_content, self.button3),
        }

        self.lista_content.conversation_selected.connect(self._abrir_conversacion)

        # Aplicar sombra
        self.apply_shadow()

        self.tray_icon = QSystemTrayIcon(self)
        icon_pixmap = create_svg_icon(icons.get_chat_icon()).pixmap(64, 64)
        self.tray_icon.setIcon(QIcon(icon_pixmap))
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Mostrar Island")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("Salir por completo")
        quit_action.triggered.connect(QApplication.instance().quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def center_window(self):
        """Centra la ventana en la parte superior de la pantalla"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - config.WINDOW_WIDTH) // 2
        y = config.WINDOW_TOP_MARGIN
        self.move(x, y)

    def create_menu_button(self):
        """Crea el botón de menú con 3 puntos verticales"""
        button = QPushButton()
        button.setFixedSize(config.MENU_BUTTON_WIDTH, config.BUTTON_SIZE)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setProperty("class", "MenuButton")
        button.setText("⋮")
        button.clicked.connect(self.on_menu_clicked)
        return button

    def apply_shadow(self):
        """Aplica el efecto de sombra a la ventana"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(config.SHADOW_BLUR_RADIUS)
        shadow.setXOffset(config.SHADOW_OFFSET_X)
        shadow.setYOffset(config.SHADOW_OFFSET_Y)
        shadow.setColor(QColor(*config.SHADOW_COLOR))
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        """Dibuja el fondo de la ventana con forma de píldora"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Ajustar el rectángulo para la sombra
        rect = self.rect().adjusted(8, 8, -8, -8)
        radius = rect.height() / 2

        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), radius, radius)

        painter.setBrush(QBrush(QColor(*config.BACKGROUND_COLOR)))
        painter.setPen(QPen(QColor(*config.BORDER_COLOR), 1.5))
        painter.drawPath(path)

        inner_path = QPainterPath()
        inner_rect = rect.adjusted(1, 1, -1, -1)
        inner_path.addRoundedRect(
            inner_rect.x(), inner_rect.y(),
            inner_rect.width(), inner_rect.height(),
            radius - 1, radius - 1
        )
        painter.setPen(QPen(QColor(*config.INNER_BORDER_COLOR), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(inner_path)


    def hideEvent(self, event):
        self.popup.hide()
        self.settings.hide()
        super().hideEvent(event)

    def mousePressEvent(self, event):
        """Permite arrastrar la ventana"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Mueve la ventana mientras se arrastra"""
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            if self.popup.isVisible():
                self.popup.reposition(self)
            event.accept()

    def on_button_clicked(self, button_name):
        """Maneja los clics en los botones principales"""
        if button_name not in self._content_map:
            return

        content, _ = self._content_map[button_name]

        if self.popup.isVisible() and self.popup._current_content is content:
            self.popup.hide()
            return

        self.popup.set_content(content)
        self.popup.show_below(self)

        if button_name == "chat":
            self.chat_content.focus_input()
        elif button_name == "lista":
            self.lista_content.refresh()

    def on_menu_clicked(self):
        """Muestra menú contextual"""
        menu = QMenu(self)

        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)

        settings_action = menu.addAction("Ajustes")
        settings_action.triggered.connect(lambda: self.settings.show_right_of(self))

        menu.addSeparator()

        close_action = menu.addAction("Minimizar")
        close_action.triggered.connect(self.settings.hide)
        close_action.triggered.connect(self.close)

        exit_action = menu.addAction("Salir")
        exit_action.triggered.connect(QApplication.instance().quit)

        menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().center()) - QPoint(menu.sizeHint().width() // 2, (-self.menu_button.height() - 20) // 2))

    def _on_macro_texto(self, texto):
        self.chat_content.insertar_texto(texto)
        self.popup.set_content(self.chat_content)
        self.chat_content.focus_input()

    def _abrir_conversacion(self, conv_id):
        self.chat_content.load_conversation(conv_id)
        self.popup.set_content(self.chat_content)
        self.chat_content.focus_input()

    def _apply_opacity(self, value: float):
        self.setWindowOpacity(value)
        self.popup.setWindowOpacity(value)
        self.settings.setWindowOpacity(value)

    def _apply_scale(self, scale: float):
        new_w = int(self._base_window_width * scale)
        new_h = int(self._base_window_height * scale)
        btn_size = int(self._base_button_size * scale)
        icon_size = int(self._base_icon_size * scale)
        menu_w = int(self._base_menu_button_width * scale)
        btn_radius = btn_size // 2
        menu_radius = int(22 * scale)
        margin_h = int(self._base_margin_h * scale)
        margin_v = int(self._base_margin_v * scale)
        spacing = int(self._base_spacing * scale)

        self.setFixedSize(new_w, new_h)
        self.main_layout.setContentsMargins(margin_h, margin_v, margin_h, margin_v)
        self.main_layout.setSpacing(spacing)

        from PySide6.QtCore import QSize
        for btn, svg in zip((self.button1, self.button2, self.button3), self._icon_svgs):
            btn.setFixedSize(btn_size, btn_size)
            btn.setIcon(create_svg_icon(svg, icon_size))
            btn.setIconSize(QSize(icon_size, icon_size))
            btn.setStyleSheet(f"border-radius: {btn_radius}px;")

        self.menu_button.setFixedSize(menu_w, btn_size)
        self.menu_button.setStyleSheet(f"border-radius: {menu_radius}px;")

        self.center_window()