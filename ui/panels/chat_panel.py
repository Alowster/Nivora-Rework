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

        self._auto_scroll = True
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

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

    def _on_scroll_changed(self, value):
        sb = self.scroll_area.verticalScrollBar()
        self._auto_scroll = value >= sb.maximum() - 30

    def _scroll_to_bottom(self):
        if self._auto_scroll:
            sb = self.scroll_area.verticalScrollBar()
            sb.setValue(sb.maximum())

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

    def enviar_mensaje(self):
        texto = self.input_field.text().strip()
        if not texto:
            return
        self._auto_scroll = True
        if self.conversation_id is None:
            self.conversation_id = create_conversation()
            rename_conversation(self.conversation_id, texto[:45] + "..." if len(texto) > 45 else texto)
            self._actualizar_nombre()
        has_capture = bool(self.ocr_context)
        add_message(self.conversation_id, "user", texto)
        self.add_bubble(texto, "user", has_capture=has_capture)
        self.input_field.clear()
        self.input_field.setEnabled(False)

        self.current_response = ""
        self.ai_bubble = self._create_ai_bubble()
        self.messages_layout.addWidget(self.ai_bubble, alignment=Qt.AlignLeft)

        historial = get_messages(self.conversation_id)
        if self.ocr_context:
            system_msg = {"role": "system", "content": f"El usuario ha capturado esta región de pantalla. Texto extraído:\n---\n{self.ocr_context}\n---"}
            historial = [system_msg] + historial
            self.ocr_context = None
        self.worker = AIService(historial)
        self.worker.chunk_received.connect(self.on_chunk)
        self.worker.completed.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.btn_stop.setVisible(True)
        self.btn_enviar.setVisible(False)
        self.worker.start()

    def detener_generacion(self):
        self._render_timer.stop()
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
        if hasattr(self, 'current_response') and self.current_response:
            add_message(self.conversation_id, "assistant", self.current_response)
            html = md.markdown(self.current_response, extensions=["fenced_code", "tables"])
            self.ai_bubble.setHtml(f'<div style="color:white;">{html}</div>')
            self._update_bubble_height(self.ai_bubble)
        self.btn_stop.setVisible(False)
        self.btn_enviar.setVisible(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def add_bubble(self, text, role, has_capture=False):
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setFixedWidth(220)
        bubble.setContentsMargins(12, 8, 12, 8)
        bubble.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        if role == "user":
            bubble.setStyleSheet("background-color: rgba(123, 104, 238, 0.18); border: 1px solid rgba(123, 104, 238, 0.25); border-radius: 12px; color: rgba(255, 255, 255, 0.90); font-size: 13px;")
        else:
            bubble.setStyleSheet("background-color: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; color: rgba(255, 255, 255, 0.80); font-size: 13px;")

        if role == "user" and has_capture:
            from PySide6.QtWidgets import QHBoxLayout, QWidget as _W
            row = _W()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            badge = QLabel("📷")
            badge.setFixedSize(24, 24)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                "background-color: rgba(123,104,238,0.30);"
                "border: 1px solid rgba(123,104,238,0.50);"
                "border-radius: 8px;"
                "font-size: 13px;"
            )
            row_layout.addStretch()
            row_layout.addWidget(badge)
            row_layout.addWidget(bubble)
            self.messages_layout.addWidget(row, alignment=Qt.AlignmentFlag.AlignRight)
        elif role == "user":
            self.messages_layout.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignRight)
        else:
            self.messages_layout.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignLeft)

        h = bubble.heightForWidth(220)
        if h > 0:
            bubble.setFixedHeight(h)

        self._scroll_to_bottom()

    def load_conversation(self, conversation_id):
        self._render_timer.stop()
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.completed.disconnect()
            self.worker.chunk_received.disconnect()
            self.worker.error.disconnect()
            self.worker.stop()
        self.btn_stop.setVisible(False)
        self.btn_enviar.setVisible(True)
        self.input_field.setEnabled(True)

        self.conversation_id = conversation_id
        self._actualizar_nombre()

        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for msg in get_messages(conversation_id):
            if msg["role"] == "user":
                self.add_bubble(msg["content"], "user")
            else:
                bubble = self._create_ai_bubble()
                html = md.markdown(msg["content"], extensions=["fenced_code", "tables"])
                bubble.setHtml(f'<div style="color:white;">{html}</div>')
                self.messages_layout.addWidget(bubble, alignment=Qt.AlignLeft)
                self._update_bubble_height(bubble)

    def nueva_conversacion(self):
        self._render_timer.stop()
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.completed.disconnect()
            self.worker.chunk_received.disconnect()
            self.worker.error.disconnect()
            self.worker.stop()
        self.btn_stop.setVisible(False)
        self.btn_enviar.setVisible(True)
        self.input_field.setEnabled(True)
        self.conversation_id = None
        self._actualizar_nombre()
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _flush_render(self):
        if self._pending_render:
            self.ai_bubble.setPlainText(self.current_response)
            self._update_bubble_height(self.ai_bubble)
            self._scroll_to_bottom()
            self._pending_render = False
        else:
            self._render_timer.stop()

    def on_chunk(self, text):
        self.current_response += text
        self._pending_render = True
        if not self._render_timer.isActive():
            self._render_timer.start()

    def on_finished(self):
        self._render_timer.stop()
        add_message(self.conversation_id, "assistant", self.current_response)
        html = md.markdown(self.current_response, extensions=["fenced_code", "tables"])
        self.ai_bubble.setHtml(f'<div style="color:white;">{html}</div>')
        self._update_bubble_height(self.ai_bubble)
        self.btn_stop.setVisible(False)
        self.btn_enviar.setVisible(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def on_error(self, error_msg):
        self.ai_bubble.setPlainText(f"Error: {error_msg}")
        self._update_bubble_height(self.ai_bubble)
        self.btn_stop.setVisible(False)
        self.btn_enviar.setVisible(True)
        self.input_field.setEnabled(True)