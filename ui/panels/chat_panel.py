import mimetypes
import tempfile

import markdown as md
from PIL import ImageGrab
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QVBoxLayout,
    QScrollArea, QLabel, QPushButton, QTextEdit, QFileDialog
)

from assets.icons import get_send_icon, get_camera_icon, get_stop_icon
from data.database import (
    create_conversation, add_message, get_messages,
    rename_conversation, get_conversation_name
)
from services.gemini_thread import GeminiThread
from ui.panels.region_selector import RegionSelector
from ui.widgets.icon_button import create_icon_button


class ChatPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.conversation_id = None
        self._pending_render = False
        self._render_timer = QTimer()
        self._render_timer.setInterval(50)
        self._render_timer.timeout.connect(self._flush_render)
        self.pending_attachments: list[dict] = []
        self.init_ui()
        self._actualizar_nombre()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

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

        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.messages_layout.setSpacing(8)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.messages_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        main_layout.addWidget(self.scroll_area)

        self._auto_scroll = True
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

        # Indicador de adjuntos pendientes
        self.lbl_attachments = QLabel("")
        self.lbl_attachments.setStyleSheet("color: rgba(255,255,255,150); font-size: 11px;")
        self.lbl_attachments.setVisible(False)
        main_layout.addWidget(self.lbl_attachments)

        # Fila de input
        input_container = QHBoxLayout()
        input_container.setSpacing(6)

        self.btn_attach = QPushButton("📎")
        self.btn_attach.setFixedSize(36, 36)
        self.btn_attach.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_attach.clicked.connect(self.adjuntar_archivo)

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

        input_container.addWidget(self.btn_attach)
        input_container.addWidget(self.input_field)
        input_container.addWidget(self.btn_stop)
        input_container.addWidget(self.btn_enviar)
        input_container.addWidget(self.btn_extra)
        main_layout.addLayout(input_container)

    # ── Adjuntos ──────────────────────────────────────────────────────────────

    def adjuntar_archivo(self):
        import os
        # Qt.WindowType.Popup cierra la ventana al perder el foco.
        # Cambiamos temporalmente a Tool para que el file dialog no cierre el panel.
        popup = self.window()
        pos = popup.pos()
        flags = popup.windowFlags()
        popup.setWindowFlags(flags & ~Qt.WindowType.Popup | Qt.WindowType.Tool)
        popup.move(pos)
        popup.show()

        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo", "",
            "Imágenes y documentos (*.png *.jpg *.jpeg *.webp *.pdf *.txt *.csv);;Todos (*)"
        )

        popup.setWindowFlags(flags)
        popup.move(pos)
        popup.show()

        if not path:
            return
        mime, _ = mimetypes.guess_type(path)
        if not mime:
            mime = "application/octet-stream"
        self.pending_attachments.append({
            "path": path,
            "mime_type": mime,
            "name": os.path.basename(path),
        })
        self._actualizar_label_adjuntos()

    def iniciar_captura(self):
        self.window().hide()
        self.selector = RegionSelector()
        self.selector.region_selected.connect(self.on_region_selected)

    def on_region_selected(self, x, y, w, h):
        self.window().show()
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(tmp.name)
        tmp.close()
        self.pending_attachments.append({
            "path": tmp.name,
            "mime_type": "image/png",
            "name": "captura.png",
        })
        self._actualizar_label_adjuntos()
        self.input_field.setFocus()

    def _actualizar_label_adjuntos(self):
        if not self.pending_attachments:
            self.lbl_attachments.setVisible(False)
            return
        nombres = ", ".join(a["name"] for a in self.pending_attachments)
        self.lbl_attachments.setText(f"📎 {nombres}")
        self.lbl_attachments.setVisible(True)

    # ── Envío ─────────────────────────────────────────────────────────────────

    def enviar_mensaje(self):
        texto = self.input_field.text().strip()
        if not texto and not self.pending_attachments:
            return
        self._auto_scroll = True

        if self.conversation_id is None:
            self.conversation_id = create_conversation()
            nombre = texto[:45] + "..." if len(texto) > 45 else texto
            rename_conversation(self.conversation_id, nombre or "Archivo adjunto")
            self._actualizar_nombre()

        add_message(self.conversation_id, "user", texto)
        self.add_bubble(texto, "user", attachments=self.pending_attachments)
        self.input_field.clear()
        self.input_field.setEnabled(False)

        # Construir historial: mensajes previos sin adjuntos + último con adjuntos
        historial = get_messages(self.conversation_id)
        if self.pending_attachments and historial:
            historial[-1] = dict(historial[-1])
            historial[-1]["attachments"] = list(self.pending_attachments)

        self.pending_attachments = []
        self._actualizar_label_adjuntos()

        self.current_response = ""
        self.ai_bubble = self._create_ai_bubble()
        self.messages_layout.addWidget(self.ai_bubble, alignment=Qt.AlignLeft)

        self.worker = GeminiThread(historial)
        self.worker.chunk_received.connect(self.on_chunk)
        self.worker.completed.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.btn_stop.setVisible(True)
        self.btn_enviar.setVisible(False)
        self.worker.start()

    # ── Burbujas ──────────────────────────────────────────────────────────────

    def add_bubble(self, text, role, attachments=None):
        if role == "user" and attachments:
            from PySide6.QtWidgets import QHBoxLayout, QWidget as _W
            row = _W()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            row_layout.addStretch()

            for att in attachments:
                badge = QLabel(f"📎 {att['name']}")
                badge.setStyleSheet(
                    "background-color: rgba(123,104,238,0.25);"
                    "border: 1px solid rgba(123,104,238,0.40);"
                    "border-radius: 8px; padding: 2px 6px;"
                    "color: white; font-size: 11px;"
                )
                row_layout.addWidget(badge)

            if text:
                bubble = self._create_user_bubble(text)
                row_layout.addWidget(bubble)

            self.messages_layout.addWidget(row, alignment=Qt.AlignmentFlag.AlignRight)
        elif role == "user":
            bubble = self._create_user_bubble(text)
            self.messages_layout.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignRight)
        else:
            bubble = QLabel(text)
            bubble.setWordWrap(True)
            bubble.setFixedWidth(220)
            bubble.setContentsMargins(12, 8, 12, 8)
            bubble.setStyleSheet("background-color: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; color: rgba(255,255,255,0.80); font-size: 13px;")
            self.messages_layout.addWidget(bubble, alignment=Qt.AlignmentFlag.AlignLeft)

        self._scroll_to_bottom()

    def _create_user_bubble(self, text):
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setFixedWidth(220)
        bubble.setContentsMargins(12, 8, 12, 8)
        bubble.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        bubble.setStyleSheet(
            "background-color: rgba(123,104,238,0.18);"
            "border: 1px solid rgba(123,104,238,0.25);"
            "border-radius: 12px; color: rgba(255,255,255,0.90); font-size: 13px;"
        )
        h = bubble.heightForWidth(220)
        if h > 0:
            bubble.setFixedHeight(h)
        return bubble

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

    # ── Streaming ─────────────────────────────────────────────────────────────

    def on_chunk(self, text):
        self.current_response += text
        self._pending_render = True
        if not self._render_timer.isActive():
            self._render_timer.start()

    def _flush_render(self):
        if self._pending_render:
            self.ai_bubble.setPlainText(self.current_response)
            self._update_bubble_height(self.ai_bubble)
            self._scroll_to_bottom()
            self._pending_render = False
        else:
            self._render_timer.stop()

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
        self._render_timer.stop()
        self.ai_bubble.setPlainText(f"Error: {error_msg}")
        self._update_bubble_height(self.ai_bubble)
        self.btn_stop.setVisible(False)
        self.btn_enviar.setVisible(True)
        self.input_field.setEnabled(True)

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

    # ── Scroll ────────────────────────────────────────────────────────────────

    def _on_scroll_changed(self, value):
        sb = self.scroll_area.verticalScrollBar()
        self._auto_scroll = value >= sb.maximum() - 30

    def _scroll_to_bottom(self):
        if self._auto_scroll:
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().maximum()
            )

    # ── Conversación ──────────────────────────────────────────────────────────

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
        self.pending_attachments = []
        self._actualizar_label_adjuntos()
        self._actualizar_nombre()
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
