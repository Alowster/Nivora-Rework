from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QVBoxLayout, QScrollArea, QLabel, QPushButton, QTextEdit
from PySide6.QtCore import Qt, QTimer
import markdown as md
from data.database import create_conversation, add_message, get_messages, rename_conversation, get_conversation_name
from services.ai_service import AIService
from services.ocr_service import OcrService
from ui.widgets.icon_button import create_icon_button
from assets.icons import get_send_icon, get_camera_icon, get_stop_icon
from ui.panels.region_selector import RegionSelector

class ChatPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.conversation_id = None
        self._pending_render = False
        self._render_timer = QTimer()
        self._render_timer.setInterval(50)
        self._render_timer.timeout.connect(self._flush_render)
        self.init_ui()
        self._actualizar_nombre()
        self.ocr_context = None

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.messages_layout.setSpacing(8)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_conv_name = QLabel()
        self.lbl_conv_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_conv_name.setStyleSheet("color: rgba(255,255,255,100); font-size: 11px;")
        main_layout.addWidget(self.lbl_conv_name)

        new_chat_btn = QPushButton("+ Nueva conversación")
        new_chat_btn.setFixedHeight(28)
        new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_chat_btn.clicked.connect(self.nueva_conversacion)
        new_chat_btn.setStyleSheet("border-radius: 12px")
        main_layout.addWidget(new_chat_btn)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.messages_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        main_layout.addWidget(self.scroll_area)

        input_container = QHBoxLayout()
        input_container.setSpacing(10)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Hazme una pregunta...")
        self.input_field.setFixedHeight(45)
        self.input_field.setObjectName("ChatInput")
        self.input_field.returnPressed.connect(self.enviar_mensaje)

        self.btn_enviar = create_icon_button(get_send_icon(), "GradientButton", "enviar", self.enviar_mensaje)
        self.btn_enviar.setObjectName("BtnEnviar")

        self.btn_extra = create_icon_button(
            get_camera_icon(), "GradientButton", "camara",
            lambda name: self.iniciar_captura()
        )
        self.btn_extra.setObjectName("BtnExtra")

        self.btn_stop = create_icon_button(get_stop_icon(), "GradientButton", "stop",
                                           lambda _: self.detener_generacion())
        self.btn_stop.setObjectName("BtnStop")
        self.btn_stop.setVisible(False)

        input_container.addWidget(self.input_field)
        input_container.addWidget(self.btn_stop)
        input_container.addWidget(self.btn_enviar)
        input_container.addWidget(self.btn_extra)
        main_layout.addLayout(input_container)

    def _actualizar_nombre(self):
        if self.conversation_id is None:
            self.lbl_conv_name.setText("")
            return
        self.lbl_conv_name.setText(get_conversation_name(self.conversation_id))

    def focus_input(self):
        self.input_field.setFocus()

    def insertar_texto(self, texto):
        self.input_field.setText(texto)
        self.input_field.setFocus()

    def iniciar_captura(self):
        self.window().hide()
        self.selector = RegionSelector()
        self.selector.region_selected.connect(self.on_region_selected)

    def on_region_selected(self, x, y, w, h):
        self.window().show()
        self.ocr_worker = OcrService(x, y, w, h)
        self.ocr_worker.completed.connect(self.on_ocr_done)
        self.ocr_worker.error.connect(lambda e: print(f"OCR error: {e}"))
        self.ocr_worker.start()

    def on_ocr_done(self, texto):
        self.ocr_context = texto
        self.input_field.setFocus()

    def _create_ai_bubble(self):
        bubble = QTextEdit()
        bubble.setReadOnly(True)
        bubble.setFixedWidth(260)
        bubble.setFixedHeight(36)
        bubble.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        bubble.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        bubble.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        bubble.setObjectName("AIBubble")
        bubble.document().setDocumentMargin(12)
        bubble.viewport().setStyleSheet("background: transparent;")
        return bubble

    def _update_bubble_height(self, bubble):
        bubble.document().setTextWidth(260)
        doc_height = int(bubble.document().size().height())
        bubble.setFixedHeight(doc_height + 20)

